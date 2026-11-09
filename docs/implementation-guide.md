# Implementation guide (for teams adopting this)

## 1. Collect quality labels for your own traffic

- Take a sample of real requests with checkable answers (extraction, classification, arithmetic, JSON).
  For open-ended requests use a judge, and calibrate it against human labels first.
- Run every candidate model on every request once. Record reply, tokens, latency and correctness
  (`scripts/run_models.py` shows the shape; `data/runs.jsonl` is the format).
- Split by request, or better by customer or time, so the test set is new traffic.

## 2. Price each model honestly

- Hosted model: per-token list price with an as-of date.
- Your own compute: measured seconds x the hourly price of the machine, divided by realistic utilisation
  (`costroute/cost.py`). Do not use 100% utilisation for a service that idles at night.

## 3. Train the router and pick a threshold

```bash
pip install -r requirements.txt
python scripts/run_eval.py      # writes results/metrics.json and results/report.md
```

Agree the quality floor with the product owner ("no more than 2 points below the big model on
validation" here), then let the eval pick the cheapest threshold that meets it. Look at the per-family
table: the router should send the hard families up.

## 4. Turn on the guardrails before go-live

- Residency: list which tiers may see personal data; extend `has_personal_data` with your own patterns
  (account numbers with checksums, national IDs).
- Strip routing directives from prompts.
- Set a budget per batch or per tenant; decide whether to downgrade or refuse.
- Put a circuit breaker on every tier with fallback to the next allowed one.

## 5. Watch it in production

Log the decision, the predicted quality and the tier for every request (without the prompt text). Sample
cheap-tier answers for review, because a well-formed wrong answer is not escalated. Re-label and retrain
when a model version or the traffic mix changes.

## 6. Optional: deploy

See [deployment.md](deployment.md). Check prices and get approval first.
