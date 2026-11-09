# ADR 0005: Residency rules apply before any cost decision

**Status:** accepted

**Context.** The cheapest-good-enough model is not always allowed to see the data.

**Decision.** `allowed_models` filters tiers first (personal data -> local tiers only), and every policy,
including always-large and the oracle, chooses only from that list.

**Consequences.** Some personal-data prompts get a weaker model than the router would pick. That is the
price of the rule and is counted in the results.
