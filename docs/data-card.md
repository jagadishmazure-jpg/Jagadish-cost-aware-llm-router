# Data card: tasks and measured runs

## Tasks (`costroute/tasks.py`, generated, not stored)

600 synthetic requests to the operations assistant of a fictional freight company, Lumenfield Freight:
100 in each of six families. Each has a reference answer, so quality is scored by code.

| Family | Example request | Scored by |
|---|---|---|
| `extract_id` | find the consignment reference in a depot note (a decoy reference is present) | exact match |
| `intent` | label a customer message as billing, delivery_delay, damage, address_change or cancellation | exactly one correct label |
| `arith1` | boxes per pallet x pallets | number |
| `arith2` | pallets x boxes - damaged boxes | number |
| `json_extract` | origin, destination and weight as JSON | all three fields |
| `date_calc` | ship date + transit days | YYYY-MM-DD |

42 tasks (in `extract_id` and `intent`) carry fake personal data: an `example.com` e-mail or a
`+44 7700 900xxx` number (a range reserved for fiction). Splits are by a hash of the task id
(about 60/20/20).

## Measured runs (`data/runs.jsonl`, 1,800 rows)

Every model answered every task once on **2026-11-09** on an 8-vCPU CPU box with llama.cpp
(`llama-cpp-python` 0.3.36, 8 threads, greedy decoding, at most 80 new tokens, one request at a time).
Each row has the reply, token counts, wall-clock latency, `correct` (reference-scored) and
`well_formed` (a format check that needs no answer, used for escalation).

| Label | Tier | Weights (GGUF Q4_K_M) | License |
|---|---|---|---|
| qwen2.5-0.5b | small (local) | Qwen2.5-0.5B-Instruct | Apache-2.0 |
| qwen2.5-1.5b | medium (local) | Qwen2.5-1.5B-Instruct | Apache-2.0 |
| phi-3.5-mini | large (in the deployment design: a Microsoft Foundry endpoint, not local) | Phi-3.5-mini-instruct (3.8B) | MIT |

URLs and SHA-256 of each file are in `scripts/models.json`. Regenerate with
`bash scripts/fetch_models.sh && python scripts/run_models.py`. Latency depends on the CPU, so
regenerated numbers will differ; the committed file is what was measured.

## Known limits

- Small models and short, templated tasks: the router learns request types easily. Real traffic is messier.
- The "large" tier is a 3.8B model, not a frontier model. Its prices and quality are not those of a hosted
  frontier model; the method carries over, the numbers do not.
- Latency was measured on a shared box; other processes ran at the same time.
