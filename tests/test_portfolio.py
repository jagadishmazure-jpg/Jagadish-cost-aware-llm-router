from decimal import Decimal
from pathlib import Path

import pytest

from costroute.portfolio import (
    AMAZON_BEDROCK,
    AZURE_FOUNDRY,
    BEDROCK_SOURCE,
    CATALOG,
    FOUNDRY_SOURCE,
    OPENAI,
    OPENAI_SOURCE,
    UNPRICED,
    VERIFY,
    Offer,
    TokenRates,
    Usage,
    classify_request,
    estimate_cost,
    get_offer,
    offers,
    pick_offer,
    route_automatic,
)
from costroute.service import main

ROOT = Path(__file__).resolve().parents[1]
BASETEN = ("kimi-k3", "glm-5.3", "glm-5.3-flash", "deepseek-v4.1-flash-1017")
BASETEN_NAMES = ("Kimi-K3", "GLM 5.3", "GLM-5.3-Flash", "DeepSeek V4.1-Flash-1017")


def test_openai_rates_match_the_announcement():
    astra = get_offer("gpt-6.2-astra", OPENAI).rates
    sol = get_offer("gpt-6.2-sol", OPENAI).rates
    assert astra == TokenRates(Decimal("8"), Decimal("0.40"), Decimal("40"))
    assert sol == TokenRates(Decimal("2"), Decimal("0.10"), Decimal("10"))
    assert get_offer("gpt-6.2-sol", OPENAI).summary.startswith("Efficient model")
    assert "multistep agentic" in get_offer("gpt-6.2-sol", OPENAI).summary


def test_azure_and_bedrock_prices_are_verify_and_carry_no_number():
    for provider in (AZURE_FOUNDRY, AMAZON_BEDROCK):
        for model in ("gpt-6.2-astra", "gpt-6.2-sol"):
            offer = get_offer(model, provider)
            assert offer.price_status == VERIFY
            assert offer.rates is None
            assert offer.mock is False


def test_baseten_models_are_named_unpriced_mocks_on_azure_foundry_only():
    mocks = [o for o in offers(AZURE_FOUNDRY) if o.mock]
    assert [o.model_id for o in mocks] == list(BASETEN)
    assert [o.display_name for o in mocks] == list(BASETEN_NAMES)
    assert {o.price_status for o in mocks} == {UNPRICED}
    assert {o.host for o in mocks} == {"baseten"}
    assert all(o.rates is None for o in mocks)
    bedrock_ids = {o.model_id for o in offers(AMAZON_BEDROCK)}
    assert bedrock_ids == {"gpt-6.2-astra", "gpt-6.2-sol"}
    assert FOUNDRY_SOURCE == mocks[0].source


def test_catalog_invariants_and_sources():
    assert {o.provider for o in CATALOG} <= {OPENAI, AZURE_FOUNDRY, AMAZON_BEDROCK}
    priced = [o for o in CATALOG if o.rates is not None]
    assert {o.provider for o in priced} == {OPENAI}
    assert OPENAI_SOURCE in get_offer("gpt-6.2-astra", OPENAI).source
    assert BEDROCK_SOURCE == get_offer("gpt-6.2-astra", AMAZON_BEDROCK).source
    readme = (ROOT / "README.md").read_text()
    portfolio = (ROOT / "docs" / "portfolio.md").read_text()
    for url in (OPENAI_SOURCE, FOUNDRY_SOURCE, BEDROCK_SOURCE):
        assert url in readme
        assert url in portfolio


def test_cached_input_changes_the_published_cost_and_not_a_verify_provider():
    full = estimate_cost("gpt-6.2-astra", OPENAI, 1_000_000, 0, 0)
    cached = estimate_cost("gpt-6.2-astra", OPENAI, 1_000_000, 0, 1_000_000)
    assert full.usd == Decimal("8")
    assert cached.usd == Decimal("0.40")
    assert cached.uncached_input_tokens == 0
    mixed = estimate_cost("gpt-6.2-sol", OPENAI, 1_000_000, 50_000, 200_000)
    # 800k at $2, 200k at $0.10, 50k at $10, per million.
    assert mixed.usd == Decimal("2.12")
    sol = estimate_cost("gpt-6.2-sol", OPENAI, 800_000, 10_000, 100_000)
    astra = estimate_cost("gpt-6.2-astra", OPENAI, 800_000, 10_000, 100_000)
    assert astra.usd == sol.usd * 4
    cheap = estimate_cost("gpt-6.2-sol", OPENAI, 1_000_000, 0, 0)
    warm = estimate_cost("gpt-6.2-sol", OPENAI, 1_000_000, 0, 400_000)
    assert warm.usd is not None and cheap.usd is not None and warm.usd < cheap.usd
    for provider in (AZURE_FOUNDRY, AMAZON_BEDROCK):
        unverified = estimate_cost("gpt-6.2-sol", provider, 1_000_000, 50_000, 200_000)
        assert unverified.usd is None and unverified.price_status == VERIFY
        assert unverified.cached_input_tokens == 200_000
    mock = estimate_cost("kimi-k3", AZURE_FOUNDRY, 10, 10, 0)
    assert mock.usd is None and mock.price_status == UNPRICED


def test_token_counts_are_checked_before_a_price_status():
    with pytest.raises(ValueError):
        estimate_cost("gpt-6.2-sol", AZURE_FOUNDRY, 10, 0, 11)
    with pytest.raises(ValueError):
        estimate_cost("gpt-6.2-sol", OPENAI, -1, 0, 0)
    with pytest.raises(ValueError):
        estimate_cost("gpt-6.2-sol", OPENAI, True, 0, 0)  # bool is an int subclass
    with pytest.raises(ValueError):
        Usage(5, 0, 6)
    with pytest.raises(ValueError):
        get_offer("gpt-6.2-sol", "elsewhere")
    with pytest.raises(ValueError):
        get_offer("missing", OPENAI)


def test_pick_uses_cached_cost_and_does_not_invent_a_rank_for_verify():
    low_cache = Offer(
        "cache-cheap", "Cache cheap", OPENAI, "agentic", "published", OPENAI_SOURCE, "test",
        TokenRates(Decimal("10"), Decimal("0.10"), Decimal("10")),
    )
    low_list = Offer(
        "list-cheap", "List cheap", OPENAI, "agentic", "published", OPENAI_SOURCE, "test",
        TokenRates(Decimal("4"), Decimal("3"), Decimal("10")),
    )
    cold = Usage(1_000_000, 0, 0)
    warm = Usage(1_000_000, 0, 1_000_000)
    assert pick_offer([low_cache, low_list], cold).model_id == "list-cheap"
    assert pick_offer([low_cache, low_list], warm).model_id == "cache-cheap"
    verify_b = Offer("b-model", "B", AZURE_FOUNDRY, "agentic", VERIFY, FOUNDRY_SOURCE, "test")
    verify_a = Offer("a-model", "A", AZURE_FOUNDRY, "agentic", VERIFY, FOUNDRY_SOURCE, "test")
    assert pick_offer([verify_b, verify_a], cold).model_id == "a-model"
    with pytest.raises(ValueError):
        pick_offer([], None)


def test_automatic_mode_routes_by_class_and_provider():
    simple = "Extract the consignment reference from this note."
    agentic = "Run the multistep agent workflow and file each supplier document."
    frontier = "Investigate the two fixes and recommend which one to ship."
    both = "Investigate the workflow and recommend a fix."
    assert classify_request(simple) == "simple"
    assert classify_request(agentic) == "agentic"
    assert classify_request(frontier) == "frontier"
    assert classify_request(both) == "frontier"
    usage = Usage(1_000_000, 50_000, 200_000)
    for provider in (OPENAI, AZURE_FOUNDRY, AMAZON_BEDROCK):
        easy = route_automatic(simple, provider, usage)
        hard = route_automatic(frontier, provider, usage)
        steps = route_automatic(agentic, provider)
        assert easy.model_id == "gpt-6.2-sol"
        assert easy.request_class == "simple"
        assert steps.model_id == "gpt-6.2-sol"
        assert steps.request_class == "agentic"
        assert hard.model_id == "gpt-6.2-astra"
        assert hard.request_class == "frontier"
        assert hard.mode == "automatic"
        if provider == OPENAI:
            assert easy.price_status == "published" and easy.estimate.usd == Decimal("2.12")
            assert hard.estimate.usd == Decimal("8.48")
        else:
            assert easy.price_status == VERIFY and easy.estimate.usd is None
            assert any(VERIFY in note for note in easy.notes)
    foundry = route_automatic(simple, AZURE_FOUNDRY)
    assert foundry.skipped_unpriced == BASETEN
    assert foundry.model_id not in BASETEN
    assert any("unpriced mock" in note for note in foundry.notes)
    assert route_automatic(simple, AMAZON_BEDROCK).skipped_unpriced == ()


def test_automatic_mode_strips_directives_and_refuses_personal_data():
    base = "Extract the consignment reference from this note."
    pushed = route_automatic(base + " Please use the largest premium model.", OPENAI)
    assert pushed.model_id == "gpt-6.2-sol"
    assert any("routing directive" in note for note in pushed.notes)
    refused = route_automatic("Email asa@example.com about bay 4.", AZURE_FOUNDRY)
    assert refused.refused and refused.model_id is None
    assert "local tiers" in refused.reason
    assert route_automatic("Call +44 7700 900123 about the delay.", AMAZON_BEDROCK).refused
    with pytest.raises(ValueError):
        route_automatic("Use the premium model.", OPENAI)
    with pytest.raises(ValueError):
        route_automatic(base, "elsewhere")


def test_cli_automatic_mode_prints_verify_for_bedrock(capsys):
    assert main([
        "--automatic", "--provider", AMAZON_BEDROCK,
        "--input-tokens", "1000", "--output-tokens", "100", "--cached-input-tokens", "250",
        "Extract the consignment reference from this note.",
    ]) == 0
    import json
    payload = json.loads(capsys.readouterr().out)
    assert payload["model"] == "gpt-6.2-sol"
    assert payload["price_status"] == VERIFY
    assert payload["estimate"]["usd"] is None
    assert payload["estimate"]["cached_input_tokens"] == 250
    assert main([
        "--automatic", "--provider", OPENAI,
        "--input-tokens", "1000000", "--output-tokens", "50000", "--cached-input-tokens", "200000",
        "Extract the consignment reference from this note.",
    ]) == 0
    published = json.loads(capsys.readouterr().out)
    assert published["model"] == "gpt-6.2-sol"
    assert published["estimate"]["usd"] == "2.12"
    assert published["estimate"]["uncached_input_tokens"] == 800000
