# Interview points

**30-second version.** I built a router that sends each LLM request to the cheapest model likely to get
it right. Three open models answered 600 logistics tasks on CPU, scored against reference answers, so
the labels are measured, not judged. A per-model quality predictor plus a threshold chosen on
validation gives 70.0%<!-- m:policies/router+escalation/accuracy/rate --> accuracy against 65.0% for always
using the large model, at 31.9%<!-- m:vs_always_large/cost_ratio --> of the cost. Budget caps, a circuit
breaker, escalation and a data-residency rule sit around it, each with a test and a CI gate.

**Design choices I would defend**

- *Replay, not re-run.* Every model answered every task once. Any policy can then be scored exactly on the
  same answers, so policy differences are not sampling noise.
- *Reference scoring, not an LLM judge.* Exact, free and repeatable. The cost is that tasks must have checkable answers.
- *Threshold from validation, with a quality floor.* "Cheapest within 2 points of always-large" is a
  business rule a FinOps lead can read; test data is never used to pick it.
- *Residency before cost.* Personal data limits the allowed tiers first, and only then does cost matter.
- *Reserve budget before the call.* Checking after the call lets one slow answer break the cap.

**Things that went wrong and what I did**

- My first phone-number pattern matched dates like 2026-07-28, so every date task was forced to the
  small tiers. Precision was 0.296. I fixed the pattern and added a test with dates; precision and recall are now 1.0.
- The first budget check ran after the call. Escalation and slow replies overran the cap. I moved to a
  reservation of 1.5x the worst measured cost, with a timeout, then downgrade, then refuse.
- Two-step arithmetic defeats every model. The router first sent those to the large model, paying more
  for nothing. Now, if every tier is predicted hopeless, it uses the cheapest and flags the request.
- The large model was worse at JSON extraction than the small ones. I kept that in the results, because
  it is the best argument for learned routing over "bigger is safer".

**What I would do next**

- Add a hosted per-token tier and open-ended tasks scored by a judge calibrated against human labels.
- Learn from production feedback (thumbs, retries) with a shadow router before switching.
- Deploy the gated Microsoft Foundry endpoint in a sandbox subscription and measure real latency.
