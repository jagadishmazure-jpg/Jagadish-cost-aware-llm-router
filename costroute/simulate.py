"""Replay routing policies over *measured* runs. Every model really answered every task, so a policy's
quality, latency and cost are exact replays, not estimates (cost uses the VM price in cost.py)."""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from .cost import CostModel
from .data import ORDER, Run
from .guardrails import Budget, CircuitBreaker, allowed_models, sanitize
from .router import QualityPredictor, pick


@dataclass
class Outcome:
    task_id: str
    family: str
    models_called: list[str]
    final_model: str | None
    correct: bool
    latency_s: float
    usd: float
    refused: str | None = None
    notes: list[str] = field(default_factory=list)


def serve(task: dict, first: str, allowed: list[str], runs: dict[tuple[str, str], Run], cost: CostModel,
          escalate: bool) -> Outcome:
    """Call `first`; if escalation is on and the reply is malformed, move up the allowed tiers."""
    called, lat = [], 0.0
    idx = allowed.index(first)
    while True:
        m = allowed[idx]
        r = runs[(task["task_id"], m)]
        called.append(m)
        lat += r.latency_s
        if not escalate or r.well_formed or idx == len(allowed) - 1:
            return Outcome(task["task_id"], task["family"], called, m, r.correct, lat, cost.usd(lat))
        idx += 1


def tiers() -> dict[str, str]:
    from .data import MODELS

    return {m["label"]: m["tier"] for m in MODELS}


def run_policy(tasks: list[dict], runs: dict, cost: CostModel, choose: Callable[[dict, list[str]], str],
               escalate: bool = False, residency: bool = True) -> list[Outcome]:
    out = []
    tier_map = tiers()
    for t in tasks:
        clean, _ = sanitize(t["prompt"])
        allowed = allowed_models(clean, tier_map) if residency else list(ORDER)
        first = choose(t, allowed)
        if first not in allowed:
            raise AssertionError("policy picked a model outside the allowed list")
        out.append(serve(t, first, allowed, runs, cost, escalate))
    return out


def fixed(model: str) -> Callable:
    return lambda t, allowed: model if model in allowed else allowed[-1]


def oracle(runs: dict) -> Callable:
    def choose(t, allowed):
        for m in allowed:
            if runs[(t["task_id"], m)].correct:
                return m
        return allowed[0]
    return choose


def random_policy(seed: int = 0) -> Callable:
    rng = random.Random(seed)
    return lambda t, allowed: rng.choice(allowed)


def learned(pred: QualityPredictor, threshold: float, tasks: list[dict]) -> Callable:
    probs = pred.predict([sanitize(t["prompt"])[0] for t in tasks])
    index = {t["task_id"]: i for i, t in enumerate(tasks)}

    def choose(t, allowed):
        i = index[t["task_id"]]
        return pick({m: probs[m][i] for m in allowed}, allowed, threshold)
    return choose


def with_budget(tasks: list[dict], runs: dict, cost: CostModel, choose: Callable, cap_usd: float,
                escalate: bool = True, headroom: float = 1.5) -> tuple[list[Outcome], Budget]:
    """Serve in order under a batch cap. The cap is enforced *before* each call.

    Each call reserves `headroom` x the worst cost seen for that model in training (`choose.worst`) and
    has a timeout at that reservation, so a call can never cost more than it reserved. If the pick does
    not fit, the cheapest allowed model that fits is used (a downgrade); if nothing fits, the request is
    refused. Escalation happens only when the next tier's reservation still fits."""
    budget = Budget(cap_usd)
    tier_map = tiers()
    worst = getattr(choose, "worst", None)
    if not worst:
        raise ValueError("choose.worst (worst training cost per model) is required")
    reserve = {m: headroom * w for m, w in worst.items()}
    out = []
    for t in tasks:
        clean, _ = sanitize(t["prompt"])
        allowed = allowed_models(clean, tier_map)
        m = choose(t, allowed)
        if reserve[m] > budget.remaining():
            fits = [a for a in allowed if reserve[a] <= budget.remaining()]
            if not fits:
                budget.refused += 1
                out.append(Outcome(t["task_id"], t["family"], [], None, False, 0.0, 0.0, refused="budget"))
                continue
            m = fits[0]
            budget.downgraded += 1
        called, lat, usd, idx = [], 0.0, 0.0, allowed.index(m)
        while True:
            mm = allowed[idx]
            r = runs[(t["task_id"], mm)]
            called.append(mm)
            c = cost.usd(r.latency_s)
            if c > reserve[mm]:  # timeout at the reservation: cost is bounded, the answer is lost
                budget.charge(reserve[mm])
                usd += reserve[mm]
                out.append(Outcome(t["task_id"], t["family"], called, None, False, lat, usd, refused="timeout"))
                break
            budget.charge(c)
            lat, usd = lat + r.latency_s, usd + c
            nxt = allowed[idx + 1] if idx + 1 < len(allowed) else None
            if escalate and not r.well_formed and nxt and reserve[nxt] <= budget.remaining():
                idx += 1
                continue
            out.append(Outcome(t["task_id"], t["family"], called, mm, r.correct, lat, usd))
            break
    return out, budget


def with_outage(tasks: list[dict], runs: dict, cost: CostModel, choose: Callable, down: str,
                window: range, breaker: bool) -> list[Outcome]:
    """Tier `down` fails for requests whose index is in `window`. With a breaker, fail over to the next
    allowed tier; without, the request fails (counted as not served and not correct)."""
    cb = CircuitBreaker()
    tier_map = tiers()
    out = []
    for i, t in enumerate(tasks):
        clean, _ = sanitize(t["prompt"])
        allowed = allowed_models(clean, tier_map)
        m = choose(t, allowed)
        failing = lambda mm: mm == down and i in window  # noqa: E731,B023
        if breaker:
            order = [m] + [a for a in allowed if a != m]
            served = None
            for cand in order:
                if not cb.available(cand):
                    continue
                if failing(cand):
                    cb.record(cand, False)
                    continue
                cb.record(cand, True)
                served = cand
                break
            if served is None:
                out.append(Outcome(t["task_id"], t["family"], [], None, False, 0.0, 0.0, refused="outage"))
                continue
            out.append(serve(t, served, allowed, runs, cost, False))
        else:
            if failing(m):
                out.append(Outcome(t["task_id"], t["family"], [m], None, False, 0.0, 0.0, refused="outage"))
                continue
            out.append(serve(t, m, allowed, runs, cost, False))
    return out


def mix(outcomes: list[Outcome]) -> dict[str, int]:
    return dict(Counter(o.final_model or "refused" for o in outcomes))
