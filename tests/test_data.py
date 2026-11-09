import json

import pytest

from costroute.data import ORDER, DataError, load_runs, tasks_with_runs, validate

GOOD = {"task_id": "arith1-000", "model": ORDER[0], "correct": True, "well_formed": True, "latency_s": 0.2,
        "prompt_tokens": 40, "completion_tokens": 3, "output": "258"}


def test_valid_record_and_int_latency():
    assert validate({**GOOD, "latency_s": 1}).latency_s == 1.0


def test_bad_records_rejected():
    for bad in ({k: v for k, v in GOOD.items() if k != "correct"}, {**GOOD, "prompt_tokens": True},
                {**GOOD, "latency_s": -1.0}, {**GOOD, "model": "mystery-70b"}, {**GOOD, "correct": 1}):
        with pytest.raises(DataError):
            validate(bad)


def test_errors_never_echo_output(tmp_path):
    secret = "asha.42@example.com"
    (tmp_path / "r.jsonl").write_text(json.dumps({**GOOD, "output": secret, "latency_s": "x"}) + "\n")
    with pytest.raises(DataError) as e:
        load_runs(tmp_path / "r.jsonl")
    assert secret not in str(e.value)


def test_duplicates_rejected(tmp_path):
    (tmp_path / "r.jsonl").write_text((json.dumps(GOOD) + "\n") * 2)
    with pytest.raises(DataError, match="duplicate"):
        load_runs(tmp_path / "r.jsonl")


def test_measured_runs_are_complete():
    runs = load_runs()
    assert len(runs) == 1800 and len(tasks_with_runs(runs)) == 600
    assert all(r.latency_s > 0 for r in runs.values())
