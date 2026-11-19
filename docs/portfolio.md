# Hosted portfolio

The measured router prices local CPU seconds. This page is the other catalog: hosted model ids,
token rates, and an automatic routing mode. Nothing here was measured on a live API. Quality for
these models is not scored.

## Sources

- OpenAI, [Introducing GPT-6.2 Astra and Sol](https://openai.com/index/introducing-gpt-6-2-astra-sol/).
  Standard API rates per million tokens: GPT-6.2 Astra $8 input, $0.40 cached input, $40 output.
  GPT-6.2 Sol $2 input, $0.10 cached input, $10 output. Sol is the efficient model for everyday
  work and multistep agentic workflows. Astra is the frontier model.
- Microsoft Foundry, [From model choice to your durable advantage](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/from-model-choice-to-your-durable-advantage-build-ai-that-keeps-improving/4573609).
  Automatic model selection sends simple requests to smaller, faster models and complex requests
  to frontier reasoning. The same post names Baseten-hosted open models: Kimi-K3, GLM 5.3,
  GLM-5.3-Flash and DeepSeek V4.1-Flash-1017. It does not publish token rates for them.
- OpenAI Academy, [GPT-6.2 Astra and GPT-6.2 Sol are now available on Bedrock](https://academy.openai.com/public/clubs/openai-on-aws/blogs/gpt-62-astra-and-gpt-62-sol-are-now-available-on-amazon-bedrock-2026-11-18).
  Availability only. The post does not publish token rates.

## Catalog

| Model | Provider id | Price status | Rates per million (input / cached input / output) |
|---|---|---|---|
| GPT-6.2 Sol | `openai` | published | $2 / $0.10 / $10 |
| GPT-6.2 Astra | `openai` | published | $8 / $0.40 / $40 |
| GPT-6.2 Sol | `azure_foundry` | [verify] | no number |
| GPT-6.2 Astra | `azure_foundry` | [verify] | no number |
| GPT-6.2 Sol | `amazon_bedrock` | [verify] | no number |
| GPT-6.2 Astra | `amazon_bedrock` | [verify] | no number |
| Kimi-K3, GLM 5.3, GLM-5.3-Flash, DeepSeek V4.1-Flash-1017 | `azure_foundry` (host `baseten`) | unpriced mock | no number |

Astra and Sol are offered on Azure Foundry and on Bedrock so a caller can name the provider. `[verify]`
means the cited page does not publish a rate this catalog will bill. The Bedrock post announces the
models without a rate. The Foundry post does not publish a rate for Sol or Astra. The OpenAI figure is
not copied onto either provider. Long-context, cache-write, regional and speed-tier rates are not
stored either: the announcement's standard input, cached-input and output rates are the only numbers.

## Cached-input cost

For a published offer:

```text
usd = (uncached input × input rate + cached input × cached rate + output × output rate) / 1_000_000
```

Uncached input is input minus cached input. Cached input cannot exceed input. On the published
rates, Sol is one quarter of Astra for the same token mix, and a larger cached share costs less
because the cached rate is lower than the input rate.

A `[verify]` or unpriced offer still checks the token counts, then returns no dollar amount.

## Automatic mode

`route_automatic` is the Foundry-style mode. It does not use the learned quality predictor, and it
does not claim a measured accuracy.

1. Strip routing directives, the same way the local router does.
2. If the prompt has an e-mail or a phone number, refuse. Hosted providers are not local tiers.
3. Classify the prompt. Frontier cues (investigate, recommend, reconcile, slides, spreadsheets,
   judgment) select Astra. Multistep, agent, workflow or tool cues select Sol. Anything else is
   simple and also selects Sol, the smaller model.
4. Stay on the requested provider. Bedrock does not list the Baseten mocks. Azure Foundry lists
   them and does not select them, because they have no price and no measured quality.
5. If the chosen offer is published and a token usage is supplied, attach the cached-input cost.
   If the offer is `[verify]`, attach the marker and no dollars.

```bash
python examples/portfolio_demo.py
python -m costroute.service --automatic --provider amazon_bedrock \
  --input-tokens 1000 --output-tokens 100 --cached-input-tokens 250 \
  "Extract the consignment reference from this note."
```

## What this does not say

- It does not say Azure Foundry or Bedrock charge the OpenAI list price.
- It does not say the Baseten models are cheap or expensive. They are names only.
- It does not change the measured accuracy, cost or latency of the local router.
