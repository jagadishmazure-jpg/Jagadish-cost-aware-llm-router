# ADR 0004: Cost = measured seconds x a dated VM list price

**Status:** accepted

**Context.** Local models have no per-token price. Made-up per-token prices would be fiction.

**Decision.** Price the CPU box as an Azure Standard_D8s_v5 Linux VM in eastus2 at its pay-as-you-go list
price ($0.384/hour, Azure Retail Prices API, 2026-11-09), assume one request at a time and full
utilisation, and keep utilisation as a parameter.

**Consequences.** Relative costs between tiers are real (they come from measured seconds). Absolute
dollars are an amortised estimate; idle time, reservations or GPUs would change them.
