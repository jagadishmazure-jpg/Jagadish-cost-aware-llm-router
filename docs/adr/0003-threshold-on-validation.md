# ADR 0003: Choose the threshold on validation with a quality floor

**Status:** accepted

**Context.** A lower threshold sends more traffic to cheap models. Picking it on test would overstate savings.

**Decision.** Pick the cheapest threshold on the validation split whose accuracy is within 2 points of
always-large on validation. Report test results for that one threshold; show the full test frontier only
as a picture.

**Consequences.** The test quality gap can be larger than 2 points; it is reported as measured.
