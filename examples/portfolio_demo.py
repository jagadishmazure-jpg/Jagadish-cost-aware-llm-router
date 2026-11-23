"""Show hosted rates, unverified providers, and automatic routing.

Run: python examples/portfolio_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from costroute.portfolio import (  # noqa: E402
    AZURE_FOUNDRY,
    OPENAI,
    Usage,
    estimate_cost,
    get_offer,
    offers,
    route_automatic,
)

USAGE = Usage(1_000_000, 50_000, 200_000)
SAMPLES = (
    ("simple", "Extract the consignment reference from this note."),
    ("agentic", "Run the multistep agent workflow and file each supplier document."),
    ("frontier", "Investigate the two fixes and recommend which one to ship."),
)


def _usd(model_id: str, provider: str) -> str:
    estimate = estimate_cost(model_id, provider, USAGE.input_tokens, USAGE.output_tokens, USAGE.cached_input_tokens)
    if estimate.usd is None:
        return estimate.price_status
    return f"${estimate.usd}"


def main() -> int:
    print("published OpenAI API rates, USD per million tokens (input / cached input / output)")
    for model_id in ("gpt-6.2-sol", "gpt-6.2-astra"):
        rates = get_offer(model_id, OPENAI).rates
        print(f"  {model_id}: ${rates.input_per_million} / ${rates.cached_input_per_million} / ${rates.output_per_million}")
    print("provider prices for the same model ids")
    for provider in (AZURE_FOUNDRY, "amazon_bedrock"):
        for model_id in ("gpt-6.2-sol", "gpt-6.2-astra"):
            print(f"  {model_id} on {provider}: {get_offer(model_id, provider).price_status}")
    names = ", ".join(o.display_name for o in offers(AZURE_FOUNDRY) if o.mock)
    print(f"unpriced Baseten mocks on azure_foundry: {names}")
    print("cost of 1,000,000 input tokens (200,000 cached) and 50,000 output tokens")
    for provider in (OPENAI, AZURE_FOUNDRY, "amazon_bedrock"):
        for model_id in ("gpt-6.2-sol", "gpt-6.2-astra"):
            print(f"  {model_id} {provider}: {_usd(model_id, provider)}")
    print("automatic routing")
    for provider in (OPENAI, AZURE_FOUNDRY, "amazon_bedrock"):
        for label, prompt in SAMPLES:
            decision = route_automatic(prompt, provider, USAGE if provider == OPENAI else None)
            cost = ""
            if decision.estimate is not None and decision.estimate.usd is not None:
                cost = f" ${decision.estimate.usd}"
            print(f"  [{label}] {provider} -> {decision.model_id} {decision.price_status}{cost}")
    skipped = route_automatic(SAMPLES[0][1], AZURE_FOUNDRY)
    print("skipped unpriced on azure_foundry: " + ", ".join(skipped.skipped_unpriced))
    refused = route_automatic("Email asa@example.com about the delay.", AZURE_FOUNDRY)
    print(f"personal data on azure_foundry: refused={str(refused.refused).lower()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
