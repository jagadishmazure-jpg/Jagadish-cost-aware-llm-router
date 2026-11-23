# ADR 0006: Hosted rates are published figures, or [verify]

**Status:** accepted

**Context.** Local cost is measured seconds times a dated VM price ([ADR 0004](0004-cost-from-measured-seconds.md)).
Hosted models need a per-token rate, and cached input is a different rate from fresh input. A cloud
portal can list a model before it lists a price. Filling that gap with the OpenAI number, or with a
guess, would bill a figure the source did not publish.

**Decision.** `costroute/portfolio.py` stores only the standard input, cached-input and output rates
from the [GPT-6.2 Astra and Sol announcement](https://openai.com/index/introducing-gpt-6-2-astra-sol/):
Astra $8 / $0.40 / $40 and Sol $2 / $0.10 / $10 per million tokens. The same model ids are offered on
Azure Foundry and on Bedrock (`amazon_bedrock`). Those offers are marked `[verify]` and hold no
number, because the [Foundry models post](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/from-model-choice-to-your-durable-advantage-build-ai-that-keeps-improving/4573609)
and the [Bedrock availability post](https://academy.openai.com/public/clubs/openai-on-aws/blogs/gpt-62-astra-and-gpt-62-sol-are-now-available-on-amazon-bedrock-2026-11-18)
do not publish the rates this catalog will bill. Baseten-hosted open models named in the Foundry post
are unpriced mocks. Automatic routing may select Sol or Astra. It never prices a `[verify]` or
unpriced offer from another provider's rate.

Replace `[verify]` only by putting a rate copied from that provider's own price page in the same
change as the status. Do not infer it.

**Consequences.** A budget can use the OpenAI list prices, including a cached-input share. It cannot
use an Azure Foundry or Bedrock dollar figure from this catalog. The learned router and its measured
results are unchanged.
