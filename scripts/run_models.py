"""Run every model on every task on CPU (llama.cpp) and record output, tokens and wall-clock latency.

Usage:
    pip install llama-cpp-python==0.3.36
    bash scripts/fetch_models.sh
    python scripts/run_models.py --models-dir models          # resumable; writes data/runs.jsonl

Greedy decoding (temperature 0), one request at a time, 8 threads, so latency is comparable across models.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from costroute.scoring import score, well_formed  # noqa: E402
from costroute.tasks import SYSTEM, build_tasks  # noqa: E402

CFG = json.loads((ROOT / "scripts/models.json").read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models-dir", type=Path, default=ROOT / "models")
    ap.add_argument("--out", type=Path, default=ROOT / "data/runs.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    from llama_cpp import Llama

    tasks = build_tasks()
    if a.limit:
        tasks = [t for i, t in enumerate(tasks) if i % (len(tasks) // a.limit) == 0][: a.limit]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    have = set()
    if a.out.exists():
        have = {(r["task_id"], r["model"]) for r in map(json.loads, a.out.read_text().splitlines())}
    s = CFG["sampling"]
    for m in CFG["tiers"]:
        todo = [t for t in tasks if (t["task_id"], m["label"]) not in have]
        if not todo:
            continue
        llm = Llama(model_path=str(a.models_dir / m["file"]), n_ctx=s["n_ctx"], n_threads=s["n_threads"],
                    verbose=False, seed=0)
        llm.create_chat_completion(messages=[{"role": "user", "content": "Hi"}], max_tokens=4)  # warm-up
        for t in todo:
            t0 = time.perf_counter()
            r = llm.create_chat_completion(
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["prompt"]}],
                temperature=s["temperature"], max_tokens=s["max_tokens"], seed=0)
            secs = time.perf_counter() - t0
            out = r["choices"][0]["message"]["content"]
            rec = {"task_id": t["task_id"], "model": m["label"], "output": out,
                   "prompt_tokens": r["usage"]["prompt_tokens"], "completion_tokens": r["usage"]["completion_tokens"],
                   "latency_s": round(secs, 3), "correct": score(t["family"], out, t["answer"]),
                   "well_formed": well_formed(t["family"], out)}
            with a.out.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        del llm


if __name__ == "__main__":
    main()
