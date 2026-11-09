# ADR 0001: Quality labels from reference answers, not an LLM judge

**Status:** accepted

**Context.** A router learns from "was this model's answer good enough?" labels. LLM judges drift, have
position and self-preference bias, and cost money.

**Decision.** Use synthetic tasks with known answers and score replies by code (`costroute/scoring.py`).

**Consequences.** Labels are exact and repeatable, but tasks must have checkable answers. Open-ended
requests (summaries, letters) would need a judge, calibrated against human labels; listed as Planned.
