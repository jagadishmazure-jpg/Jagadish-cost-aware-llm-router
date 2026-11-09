"""Route one prompt: the same logic the eval replays, packaged for the CLI and the endpoint."""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache

from .data import ORDER, load_runs, tasks_with_runs
from .guardrails import allowed_models, has_personal_data, sanitize
from .router import HOPELESS, QualityPredictor, pick
from .simulate import tiers

DEFAULT_THRESHOLD_FILE = "results/metrics.json"


@lru_cache(maxsize=1)
def default_router() -> tuple[QualityPredictor, float]:
    from .data import ROOT

    runs = load_runs()
    train = [t for t in tasks_with_runs(runs) if t["split"] == "train"]
    pred = QualityPredictor(ORDER).fit([sanitize(t["prompt"])[0] for t in train],
                                       {m: [runs[(t["task_id"], m)].correct for t in train] for m in ORDER})
    threshold = json.loads((ROOT / DEFAULT_THRESHOLD_FILE).read_text())["threshold"]["chosen"]
    return pred, threshold


def route(prompt: str) -> dict:
    pred, threshold = default_router()
    clean, notes = sanitize(prompt)
    if not clean:
        raise ValueError("prompt is empty after removing routing directives")
    allowed = allowed_models(clean, tiers())
    probs = {m: float(v[0]) for m, v in pred.predict([clean]).items()}
    model = pick({m: probs[m] for m in allowed}, allowed, threshold)
    return {"model": model, "tier": tiers()[model], "threshold": threshold,
            "predicted_quality": {m: round(p, 3) for m, p in probs.items()},
            "allowed": allowed, "local_only": has_personal_data(clean), "notes": notes,
            "escalate_to": allowed[allowed.index(model) + 1:],
            "low_confidence": max(probs[m] for m in allowed) < HOPELESS}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pick the cheapest model likely to answer a prompt well.")
    ap.add_argument("prompt")
    a = ap.parse_args(argv)
    print(json.dumps(route(a.prompt), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
