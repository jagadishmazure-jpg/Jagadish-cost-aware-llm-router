"""Hosted portfolio: published token rates, unverified cloud rates, and automatic routing.

The learned router in `router.py` prices local CPU time. This module is separate. It records
list prices only when a cited page publishes them.

OpenAI's GPT-6.2 announcement publishes standard API rates per million tokens:

- GPT-6.2 Astra: $8 input, $0.40 cached input, $40 output. Frontier work.
- GPT-6.2 Sol: $2 input, $0.10 cached input, $10 output. Everyday work and multistep agentic work.

Azure Foundry and Bedrock list a provider for the same model ids. The Foundry models post and the
Bedrock availability post do not publish token rates, so those offers are `[verify]` and have no
number. The estimator will not reuse the OpenAI rate for them.

Baseten-hosted open models named in the Foundry models post (Kimi-K3, GLM 5.3, GLM-5.3-Flash,
DeepSeek V4.1-Flash-1017) are mock catalog rows on Azure Foundry. They are unpriced and are never
chosen by automatic routing.

Automatic routing follows the Foundry description: simple requests go to the smaller, faster model
and complex requests go to frontier reasoning. Sol is that smaller model, and it is also the model
aimed at multistep agentic work. Astra is the frontier model. Personal data never leaves the local
tiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from .guardrails import has_personal_data, sanitize

PUBLISHED = "published"
VERIFY = "[verify]"
UNPRICED = "unpriced"
MODE_AUTOMATIC = "automatic"

OPENAI = "openai"
AZURE_FOUNDRY = "azure_foundry"
AMAZON_BEDROCK = "amazon_bedrock"
PROVIDERS = (OPENAI, AZURE_FOUNDRY, AMAZON_BEDROCK)

OPENAI_SOURCE = "https://openai.com/index/introducing-gpt-6-2-astra-sol/"
FOUNDRY_SOURCE = (
    "https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/"
    "from-model-choice-to-your-durable-advantage-build-ai-that-keeps-improving/4573609"
)
BEDROCK_SOURCE = (
    "https://academy.openai.com/public/clubs/openai-on-aws/blogs/"
    "gpt-62-astra-and-gpt-62-sol-are-now-available-on-amazon-bedrock-2026-11-18"
)

_MILLION = Decimal(1_000_000)
_FRONTIER = re.compile(
    r"\b(?:investigat(?:e|es|ed|ing|ion)|weigh(?:s|ing)?|recommend(?:s|ed|ing|ation)?|"
    r"reconcil(?:e|es|ed|ing|iation)|spreadsheets?|slides?|workbooks?|memos?|judg(?:e)?ments?)\b",
    re.I,
)
_AGENTIC = re.compile(r"\b(?:agents?|agentic|multistep|multi-step|workflows?|tools?)\b", re.I)
# Foundry sends simple work to a smaller model and hard judgment to a frontier model.
# Sol is the smaller model and the one aimed at multistep agentic work.
_CLASS_ROLE = {"simple": "agentic", "agentic": "agentic", "frontier": "frontier"}


@dataclass(frozen=True)
class TokenRates:
    """Standard rates in USD per million tokens. Cached input is not the full input rate."""

    input_per_million: Decimal
    cached_input_per_million: Decimal
    output_per_million: Decimal

    def __post_init__(self) -> None:
        for name in ("input_per_million", "cached_input_per_million", "output_per_million"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or value <= 0:
                raise ValueError(f"{name} must be a positive Decimal")
        if self.cached_input_per_million > self.input_per_million:
            raise ValueError("cached input rate cannot exceed the input rate")

    def usd(self, input_tokens: int, cached_input_tokens: int, output_tokens: int) -> Decimal:
        uncached = input_tokens - cached_input_tokens
        return (
            Decimal(uncached) * self.input_per_million
            + Decimal(cached_input_tokens) * self.cached_input_per_million
            + Decimal(output_tokens) * self.output_per_million
        ) / _MILLION


@dataclass(frozen=True)
class Offer:
    model_id: str
    display_name: str
    provider: str
    role: str
    price_status: str
    source: str
    summary: str
    rates: TokenRates | None = None
    mock: bool = False
    host: str | None = None

    def __post_init__(self) -> None:
        if self.provider not in PROVIDERS:
            raise ValueError(f"unknown provider: {self.provider}")
        if self.role not in {"frontier", "agentic", "open"}:
            raise ValueError(f"unknown role: {self.role}")
        if self.price_status not in {PUBLISHED, VERIFY, UNPRICED}:
            raise ValueError(f"unknown price status: {self.price_status}")
        if self.price_status == PUBLISHED and self.rates is None:
            raise ValueError(f"{self.model_id} is published but has no rates")
        if self.price_status != PUBLISHED and self.rates is not None:
            raise ValueError(f"{self.model_id} on {self.provider} must not carry a rate")
        if self.mock and self.price_status != UNPRICED:
            raise ValueError("a mock provider has no price")


def _rates(inp: str, cached: str, out: str) -> TokenRates:
    return TokenRates(Decimal(inp), Decimal(cached), Decimal(out))


_ASTRA = _rates("8", "0.40", "40")
_SOL = _rates("2", "0.10", "10")

_ASTRA_SUMMARY = "Frontier model for the hardest professional work."
_SOL_SUMMARY = "Efficient model for everyday work and multistep agentic workflows."
_VERIFY_AZURE = (
    "Offered on Azure Foundry. The cited Foundry post does not publish a token rate for this model, "
    "so the price is [verify]."
)
_VERIFY_BEDROCK = (
    "Available on Bedrock. The availability post does not publish a token rate, so the price is [verify]."
)


def _mock(model_id: str, display_name: str) -> Offer:
    return Offer(
        model_id, display_name, AZURE_FOUNDRY, "open", UNPRICED, FOUNDRY_SOURCE,
        "Baseten-hosted open model named in the Foundry models post. Unpriced mock.",
        mock=True, host="baseten",
    )


CATALOG: tuple[Offer, ...] = (
    Offer("gpt-6.2-sol", "GPT-6.2 Sol", OPENAI, "agentic", PUBLISHED, OPENAI_SOURCE, _SOL_SUMMARY, _SOL),
    Offer("gpt-6.2-astra", "GPT-6.2 Astra", OPENAI, "frontier", PUBLISHED, OPENAI_SOURCE, _ASTRA_SUMMARY, _ASTRA),
    Offer("gpt-6.2-sol", "GPT-6.2 Sol", AZURE_FOUNDRY, "agentic", VERIFY, FOUNDRY_SOURCE,
          _SOL_SUMMARY + " " + _VERIFY_AZURE),
    Offer("gpt-6.2-astra", "GPT-6.2 Astra", AZURE_FOUNDRY, "frontier", VERIFY, FOUNDRY_SOURCE,
          _ASTRA_SUMMARY + " " + _VERIFY_AZURE),
    Offer("gpt-6.2-sol", "GPT-6.2 Sol", AMAZON_BEDROCK, "agentic", VERIFY, BEDROCK_SOURCE,
          _SOL_SUMMARY + " " + _VERIFY_BEDROCK),
    Offer("gpt-6.2-astra", "GPT-6.2 Astra", AMAZON_BEDROCK, "frontier", VERIFY, BEDROCK_SOURCE,
          _ASTRA_SUMMARY + " " + _VERIFY_BEDROCK),
    _mock("kimi-k3", "Kimi-K3"),
    _mock("glm-5.3", "GLM 5.3"),
    _mock("glm-5.3-flash", "GLM-5.3-Flash"),
    _mock("deepseek-v4.1-flash-1017", "DeepSeek V4.1-Flash-1017"),
)


def offers(provider: str | None = None) -> tuple[Offer, ...]:
    if provider is None:
        return CATALOG
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider: {provider}")
    return tuple(o for o in CATALOG if o.provider == provider)


def get_offer(model_id: str, provider: str) -> Offer:
    for offer in offers(provider):
        if offer.model_id == model_id:
            return offer
    raise ValueError(f"no offer for model {model_id!r} on provider {provider!r}")


def _count(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0

    def __post_init__(self) -> None:
        _count("input_tokens", self.input_tokens)
        _count("output_tokens", self.output_tokens)
        _count("cached_input_tokens", self.cached_input_tokens)
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input tokens cannot exceed input tokens")


@dataclass(frozen=True)
class CostEstimate:
    model_id: str
    provider: str
    input_tokens: int
    cached_input_tokens: int
    uncached_input_tokens: int
    output_tokens: int
    usd: Decimal | None
    price_status: str


def estimate_cost(model_id: str, provider: str, input_tokens: int, output_tokens: int,
                  cached_input_tokens: int = 0) -> CostEstimate:
    """USD for one call. Cached input is billed at the cached rate, and only when that rate is published.

    `[verify]` and `unpriced` offers validate the token counts and return `usd=None`. They do not
    borrow another provider's rate.
    """
    offer = get_offer(model_id, provider)
    incoming = _count("input_tokens", input_tokens)
    outgoing = _count("output_tokens", output_tokens)
    cached = _count("cached_input_tokens", cached_input_tokens)
    if cached > incoming:
        raise ValueError("cached input tokens cannot exceed input tokens")
    usd = None
    if offer.price_status == PUBLISHED:
        if offer.rates is None:
            raise ValueError(f"{model_id} is published but has no rates")
        usd = offer.rates.usd(incoming, cached, outgoing)
    return CostEstimate(model_id, provider, incoming, cached, incoming - cached, outgoing, usd, offer.price_status)


def classify_request(prompt: str) -> str:
    """`frontier` for hard judgment, `agentic` for multistep work, otherwise `simple`."""
    if _FRONTIER.search(prompt):
        return "frontier"
    if _AGENTIC.search(prompt):
        return "agentic"
    return "simple"


def _list_price(offer: Offer) -> tuple[Decimal, str]:
    if offer.rates is None:
        raise ValueError(f"{offer.model_id} is published but has no rates")
    return (offer.rates.input_per_million + offer.rates.output_per_million, offer.model_id)


def _billed(offer: Offer, usage: Usage) -> tuple[Decimal, str]:
    if offer.rates is None:
        raise ValueError(f"{offer.model_id} is published but has no rates")
    usd = offer.rates.usd(usage.input_tokens, usage.cached_input_tokens, usage.output_tokens)
    return (usd, offer.model_id)


def pick_offer(candidates: list[Offer] | tuple[Offer, ...], usage: Usage | None) -> Offer:
    """Cheapest published candidate for this usage. Unverified rows are not ranked by a guessed price."""
    if not candidates:
        raise ValueError("no eligible model")
    published = [o for o in candidates if o.price_status == PUBLISHED and o.rates is not None]
    if not published:
        return min(candidates, key=lambda o: o.model_id)
    if usage is None:
        return min(published, key=_list_price)
    return min(published, key=lambda o: _billed(o, usage))


@dataclass(frozen=True)
class AutoDecision:
    mode: str
    provider: str
    model_id: str | None
    request_class: str
    price_status: str | None
    estimate: CostEstimate | None
    candidates: tuple[str, ...]
    skipped_unpriced: tuple[str, ...]
    notes: tuple[str, ...]
    refused: bool = False
    reason: str | None = None


def route_automatic(prompt: str, provider: str, usage: Usage | None = None) -> AutoDecision:
    """Foundry-style automatic selection for one provider.

    Simple and multistep agentic prompts select Sol. Frontier prompts select Astra. When the
    chosen provider has a published rate and `usage` is set, the decision carries a cached-input
    cost. Mock and unpriced rows are listed as skipped, not selected.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider: {provider}")
    clean, notes = sanitize(prompt)
    if not clean:
        raise ValueError("prompt is empty after removing routing directives")
    request_class = classify_request(clean)
    catalog = offers(provider)
    skipped = tuple(o.model_id for o in catalog if o.mock or o.price_status == UNPRICED)
    if has_personal_data(clean):
        return AutoDecision(
            MODE_AUTOMATIC, provider, None, request_class, None, None, (), skipped, tuple(notes),
            True, "personal data stays on local tiers; hosted providers are not allowed",
        )
    role = _CLASS_ROLE[request_class]
    pool = [o for o in catalog if not o.mock and o.price_status != UNPRICED and o.role == role]
    chosen = pick_offer(pool, usage)
    estimate = None
    if usage is not None:
        estimate = estimate_cost(
            chosen.model_id, provider, usage.input_tokens, usage.output_tokens, usage.cached_input_tokens,
        )
    extra = list(notes)
    if chosen.price_status == VERIFY:
        extra.append("provider token rates are [verify]; no dollar estimate")
    if skipped:
        extra.append("unpriced mock providers were not selected")
    return AutoDecision(
        MODE_AUTOMATIC, provider, chosen.model_id, request_class, chosen.price_status, estimate,
        tuple(o.model_id for o in pool), skipped, tuple(extra),
    )
