"""Route one prompt: the same logic the eval replays, packaged for the CLI and the endpoint."""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache

from .data import ORDER, load_runs, tasks_with_runs
from .guardrails import allowed_models, has_personal_data, sanitize
from .portfolio import PROVIDERS, Usage, route_automatic
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


def route_automatic_request(prompt: str, provider: str, input_tokens: int | None = None,
                            output_tokens: int | None = None, cached_input_tokens: int = 0) -> dict:
    """Automatic hosted selection. Token counts are optional; without them there is no dollar estimate."""
    if (input_tokens is None) != (output_tokens is None):
        raise ValueError("input_tokens and output_tokens are both required to estimate cost")
    usage = None
    if input_tokens is not None and output_tokens is not None:
        usage = Usage(input_tokens, output_tokens, cached_input_tokens)
    decision = route_automatic(prompt, provider, usage)
    estimate = None
    if decision.estimate is not None:
        usd = decision.estimate.usd
        estimate = {
            "usd": None if usd is None else format(usd, "f"),
            "price_status": decision.estimate.price_status,
            "input_tokens": decision.estimate.input_tokens,
            "cached_input_tokens": decision.estimate.cached_input_tokens,
            "uncached_input_tokens": decision.estimate.uncached_input_tokens,
            "output_tokens": decision.estimate.output_tokens,
        }
    return {
        "mode": decision.mode, "provider": decision.provider, "model": decision.model_id,
        "request_class": decision.request_class, "price_status": decision.price_status,
        "estimate": estimate, "candidates": list(decision.candidates),
        "skipped_unpriced": list(decision.skipped_unpriced), "notes": list(decision.notes),
        "refused": decision.refused, "reason": decision.reason,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pick the cheapest model likely to answer a prompt well.")
    ap.add_argument("prompt")
    ap.add_argument("--automatic", action="store_true",
                    help="Foundry-style automatic selection across the hosted portfolio")
    ap.add_argument("--provider", default="azure_foundry", choices=PROVIDERS)
    ap.add_argument("--input-tokens", type=int)
    ap.add_argument("--output-tokens", type=int)
    ap.add_argument("--cached-input-tokens", type=int, default=0)
    a = ap.parse_args(argv)
    if not a.automatic and (a.input_tokens is not None or a.output_tokens is not None or a.cached_input_tokens):
        ap.error("token counts are only used with --automatic")
    if a.automatic:
        payload = route_automatic_request(
            a.prompt, a.provider, a.input_tokens, a.output_tokens, a.cached_input_tokens,
        )
    else:
        payload = route(a.prompt)
    print(json.dumps(payload, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
