import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def metrics():
    return json.loads((ROOT / "results/metrics.json").read_text())


@pytest.fixture
def toy():
    """Three tasks x three models with hand-set outcomes, for exact replay tests."""
    from costroute.data import ORDER, Run

    tasks = [{"task_id": f"t{i}", "family": "arith1", "prompt": f"How many boxes on {i} pallets?", "answer": "1",
              "has_pii": False, "split": "test"} for i in range(3)]
    spec = {  # (correct, well_formed, latency) per model, cheapest first
        "t0": [(True, True, 1.0), (True, True, 2.0), (True, True, 8.0)],
        "t1": [(False, False, 1.0), (True, True, 2.0), (True, True, 8.0)],
        "t2": [(False, True, 1.0), (False, False, 2.0), (True, True, 8.0)],
    }
    runs = {(tid, m): Run(tid, m, c, w, lat, 10, 5, "x") for tid, rows in spec.items()
            for m, (c, w, lat) in zip(ORDER, rows, strict=True)}
    return tasks, runs
