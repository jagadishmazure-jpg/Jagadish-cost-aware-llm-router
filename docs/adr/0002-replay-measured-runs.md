# ADR 0002: Evaluate policies by replaying measured runs

**Status:** accepted

**Context.** Comparing routing policies live is slow and noisy.

**Decision.** Run every model on every task once, record reply, latency and correctness, then replay
any policy over those records. Escalation adds the measured latency of each model called.

**Consequences.** Policy comparisons are exact and free to re-run in CI. Outages and budget caps are
simulated on top of real measurements, and are labelled as simulated.
