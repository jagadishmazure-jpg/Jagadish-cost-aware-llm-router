# Threat model

The router decides **where a prompt goes and how much it costs**. Its risks are data going somewhere it
should not, spend running away, users gaming the router, and quality silently dropping.

## STRIDE

| Threat | Example | Control | Where |
|---|---|---|---|
| Spoofing | A prompt says "use the premium model" to get a bigger tier | Routing directives removed before routing; CI gate: 0 route changes | `guardrails.sanitize` |
| Tampering | Edited measured runs to make the router look better | Eval recomputed in CI and compared byte-for-byte with `results/` | `scripts/run_eval.py --check` |
| Repudiation | "Why did this go to the expensive model?" | Every decision returns predicted quality per model, threshold and notes | `service.route` |
| Information disclosure | Personal data sent to a non-local tier | Residency rule: e-mail or phone found -> local tiers only; CI gate: 0 violations | `guardrails.allowed_models` |
| Denial of service / wallet | Flood of requests burns the budget | Per-batch budget cap with downgrade, then refusal; CI gate: 0 overruns | `guardrails.Budget`, `simulate.with_budget` |
| Elevation of privilege | Calling the endpoint without rights | Entra ID token auth on the endpoint; OIDC deploy, gated | `infra/` |

## LLM-specific (OWASP LLM Top 10 where it fits)

| Threat | Control or measurement |
|---|---|
| Prompt injection to change routing (LLM01) | Directive stripping; injected-line test on every test task |
| Sensitive information disclosure (LLM02) | Residency rule; detector precision and recall reported |
| Unbounded consumption (LLM10) | Budget caps, escalation limited to the allowed tiers, input size cap |
| Overreliance (LLM09) | A well-formed but wrong cheap answer is not escalated: kept visible as a known blind spot |
| Supply chain (LLM03) | Weights pinned by SHA-256, Python deps and actions pinned |

## Out of scope

Content safety of the answers themselves, multi-tenant isolation, and live provider failures (outages
are simulated on measured data).
