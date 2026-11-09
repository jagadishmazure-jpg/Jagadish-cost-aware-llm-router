"""Load measured runs and join them with the task bank."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .tasks import build_tasks

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "runs.jsonl"
MODELS = json.loads((ROOT / "scripts" / "models.json").read_text())["tiers"]
ORDER = [m["label"] for m in MODELS]  # cheapest first (small, medium, large)


class DataError(ValueError):
    """A run record failed validation. Messages never include prompt or output text."""


@dataclass(frozen=True)
class Run:
    task_id: str
    model: str
    correct: bool
    well_formed: bool
    latency_s: float
    prompt_tokens: int
    completion_tokens: int
    output: str


FIELDS = {"task_id": str, "model": str, "correct": bool, "well_formed": bool, "latency_s": float,
          "prompt_tokens": int, "completion_tokens": int, "output": str}


def validate(rec: dict) -> Run:
    for k, typ in FIELDS.items():
        if k not in rec:
            raise DataError(f"run {rec.get('task_id', '?')}: missing '{k}'")
        v = rec[k]
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if typ is not bool and isinstance(v, bool) or not isinstance(v, typ):
            raise DataError(f"run {rec.get('task_id', '?')}: '{k}' has wrong type")
        if typ is float and (math.isnan(v) or v < 0):
            raise DataError(f"run {rec['task_id']}: '{k}' must be a non-negative number")
    if rec["model"] not in ORDER:
        raise DataError(f"run {rec['task_id']}: unknown model")
    return Run(**{k: (float(rec[k]) if FIELDS[k] is float else rec[k]) for k in FIELDS})


def load_runs(path: Path = RUNS) -> dict[tuple[str, str], Run]:
    out = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = validate(json.loads(line))
        except json.JSONDecodeError as e:
            raise DataError(f"{path.name}:{n}: not valid JSON") from e
        key = (r.task_id, r.model)
        if key in out:
            raise DataError(f"{path.name}:{n}: duplicate run")
        out[key] = r
    return out


def tasks_with_runs(runs: dict[tuple[str, str], Run]) -> list[dict]:
    """Tasks that every model has a run for (all of them, when data is complete)."""
    return [t for t in build_tasks() if all((t["task_id"], m) in runs for m in ORDER)]
