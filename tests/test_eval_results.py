"""Checks on the committed results. Known misses are asserted on purpose so they stay visible."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_eval import gate  # noqa: E402


def test_gate_passes_and_router_is_cheaper(metrics):
    assert gate(metrics) == []
    assert metrics["vs_always_large"]["cost_ratio"] < 1


def test_router_beats_random_and_stays_below_oracle(metrics):
    p = metrics["policies"]
    assert p["random"]["accuracy"]["rate"] < p["router+escalation"]["accuracy"]["rate"] <= p["oracle"]["accuracy"]["rate"]


def test_known_miss_no_tier_solves_two_step_arithmetic(metrics):
    # KNOWN MISS: answer-only two-step arithmetic defeats every tier, so routing cannot help. Fix = a
    # calculator tool or allowing working, not a bigger model of this size.
    assert all(m["by_family"]["arith2"]["k"] == 0 for m in metrics["per_model"].values())


def test_known_miss_router_loses_some_tasks_large_got_right(metrics):
    assert metrics["vs_always_large"]["router_wrong_large_right"] > 0


def test_known_miss_escalation_rarely_fires(metrics):
    # Format checks cannot catch well-formed wrong answers, so escalation adds little here.
    assert metrics["policies"]["router+escalation"]["escalated"] <= 5


def test_breaker_keeps_service_up_and_tight_budget_refuses(metrics):
    o = metrics["outage"]
    assert o["breaker_fallback"]["served"]["rate"] == 1.0 > o["no_fallback"]["served"]["rate"]
    assert metrics["budget_tight"]["refused"] > 0 and metrics["budget_tight"]["within_cap"]


def test_quality_predictor_ranks_well(metrics):
    assert all(v["auc"] > 0.85 for v in metrics["predictor"].values())


def test_mix_counts_add_up(metrics):
    n = metrics["data"]["test"]
    assert all(sum(p["mix"].values()) == n for p in metrics["policies"].values())


def test_threshold_was_chosen_on_validation(metrics):
    from costroute.evaluate import GRID

    assert metrics["threshold"]["chosen"] in GRID and metrics["threshold"]["quality_floor_gap"] == 0.02


def test_cost_model_is_dated(metrics):
    c = metrics["cost_model"]
    assert c["price_as_of"] == "2026-11-09" and c["usd_per_hour"] == 0.384 and c["utilisation"] == 1.0
