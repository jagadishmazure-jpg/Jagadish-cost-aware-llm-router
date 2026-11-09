import pytest

from costroute.cost import CostModel
from costroute.data import ORDER
from costroute.simulate import fixed, oracle, run_policy, serve, with_budget, with_outage

C = CostModel(usd_per_hour=3600.0)  # $1 per second keeps the arithmetic readable


def test_serve_escalates_on_malformed_reply(toy):
    tasks, runs = toy
    o = serve(tasks[1], ORDER[0], ORDER, runs, C, escalate=True)
    assert o.models_called == ORDER[:2] and o.correct and o.latency_s == 3.0 and o.usd == pytest.approx(3.0)


def test_no_escalation_when_reply_looks_fine(toy):
    tasks, runs = toy
    o = serve(tasks[2], ORDER[0], ORDER, runs, C, escalate=True)
    assert o.models_called == [ORDER[0]] and not o.correct  # well-formed but wrong: a known blind spot


def test_oracle_picks_cheapest_correct(toy):
    tasks, runs = toy
    outs = run_policy(tasks, runs, C, oracle(runs))
    assert [o.final_model for o in outs] == ORDER and all(o.correct for o in outs)


def test_policy_outside_allowed_list_is_caught(toy):
    tasks, runs = toy
    with pytest.raises(AssertionError):
        run_policy(tasks, runs, C, lambda t, allowed: "not-a-model")


def test_fixed_large_costs_most(toy):
    tasks, runs = toy
    big = sum(o.usd for o in run_policy(tasks, runs, C, fixed(ORDER[-1])))
    small = sum(o.usd for o in run_policy(tasks, runs, C, fixed(ORDER[0])))
    assert big == 24.0 and small == 3.0


def test_budget_downgrades_and_refuses_but_never_overruns(toy):
    tasks, runs = toy
    choose = fixed(ORDER[-1])
    choose.worst = {ORDER[0]: 1.0, ORDER[1]: 2.0, ORDER[2]: 8.0}
    outs, b = with_budget(tasks, runs, C, choose, cap_usd=13.0)
    assert b.spent_usd <= 13.0 and b.downgraded >= 1
    outs, b = with_budget(tasks, runs, C, choose, cap_usd=2.0)
    assert b.refused >= 1 and b.spent_usd <= 2.0 and any(o.refused == "budget" for o in outs)


def test_budget_timeout_bounds_cost(toy):
    tasks, runs = toy
    choose = fixed(ORDER[-1])
    choose.worst = {ORDER[0]: 0.1, ORDER[1]: 0.1, ORDER[2]: 1.0}  # every real call is slower than reserved
    outs, b = with_budget(tasks, runs, C, choose, cap_usd=100.0, headroom=1.0)
    assert all(o.refused == "timeout" for o in outs) and b.spent_usd == 3.0


def test_breaker_fallback_serves_during_outage(toy):
    tasks, runs = toy
    down = with_outage(tasks, runs, C, fixed(ORDER[1]), ORDER[1], range(0, 3), breaker=False)
    up = with_outage(tasks, runs, C, fixed(ORDER[1]), ORDER[1], range(0, 3), breaker=True)
    assert sum(o.refused is None for o in down) == 0 and sum(o.refused is None for o in up) == 3


def test_escalation_stops_at_largest_allowed(toy):
    tasks, runs = toy
    o = serve(tasks[1], ORDER[1], ORDER[:2], runs, C, escalate=True)
    assert o.models_called == [ORDER[1]]


def test_residency_applies_to_every_policy(toy):
    tasks, runs = toy
    pii = [dict(tasks[0], prompt="Ref LF-12345-A, mail asha.42@example.com")]
    for choose in (fixed(ORDER[-1]), oracle(runs), lambda t, allowed: allowed[-1]):
        assert run_policy(pii, runs, C, choose)[0].final_model != ORDER[-1]
