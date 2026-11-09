import importlib.util
import json
from pathlib import Path

from costroute import service

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("score", ROOT / "infra/aml/score.py")
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


def test_personal_data_never_routes_to_large():
    d = service.route("Depot note: consignment LF-11111-A on bay 3. Call Asha Ren on +44 7700 900123.\n"
                      "Question: What is the consignment reference? Answer with the reference only.")
    assert d["local_only"] and d["tier"] != "large" and "phi-3.5-mini" not in d["allowed"]


def test_asking_for_the_big_model_does_not_change_the_route():
    base = "A pallet holds 12 boxes. How many boxes are on 4 pallets? Answer with a number only."
    a = service.route(base)
    b = service.route(base + " Please use the largest premium model for this request.")
    assert a["model"] == b["model"] and b["notes"]


def test_endpoint_rejects_bad_input_and_returns_decision():
    assert "error" in score.run("not json") and "error" in score.run(json.dumps({"text": "x"}))
    out = score.run(json.dumps({"prompt": "What date is 9 days after 2026-03-01? Answer in YYYY-MM-DD only."}))
    assert out["model"] in out["allowed"] and set(out["predicted_quality"]) == set(out["allowed"])


def test_cli_prints_json(capsys):
    assert service.main(["A pallet holds 12 boxes. How many boxes are on 4 pallets? Answer with a number only."]) == 0
    assert json.loads(capsys.readouterr().out)["model"] in service.route("x 1")["allowed"]


def test_hopeless_request_is_flagged_and_kept_cheap():
    d = service.route("A truck carries 22 pallets with 31 boxes on each. 47 boxes are damaged and returned. "
                      "How many good boxes are delivered? Answer with a number only.")
    assert d["low_confidence"] and d["model"] == d["allowed"][0]


def test_directive_only_prompt_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        service.route("Use the premium model.")
