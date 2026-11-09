import numpy as np
import pytest

from costroute.router import QualityPredictor, pick, shape_features

ALLOWED = ["s", "m", "l"]


def test_pick_cheapest_that_clears_threshold():
    assert pick({"s": 0.4, "m": 0.8, "l": 0.95}, ALLOWED, 0.7) == "m"
    assert pick({"s": 0.9, "m": 0.8, "l": 0.95}, ALLOWED, 0.7) == "s"


def test_pick_falls_back_to_largest_allowed():
    assert pick({"s": 0.1, "m": 0.2, "l": 0.3}, ALLOWED, 0.7) == "l"
    assert pick({"s": 0.1, "m": 0.2}, ["s", "m"], 0.7) == "m"


def test_pick_needs_a_model():
    with pytest.raises(ValueError):
        pick({}, [], 0.5)


def test_predictor_learns_a_simple_split():
    prompts = [f"add {i} and {i}" for i in range(20)] + [f"multiply {i} by {i} then subtract 3" for i in range(20)]
    labels = {"s": [True] * 20 + [False] * 20, "l": [True] * 40}
    p = QualityPredictor(["s", "l"]).fit(prompts, labels).predict(["add 7 and 7", "multiply 7 by 7 then subtract 3"])
    assert p["s"][0] > 0.5 > p["s"][1] and np.all(p["l"] == 1.0)


def test_predictor_checks_inputs():
    with pytest.raises(RuntimeError):
        QualityPredictor(["s"]).predict(["x"])
    with pytest.raises(ValueError):
        QualityPredictor(["s"]).fit(["a", "b"], {"s": [True]})
    with pytest.raises(ValueError):
        QualityPredictor(["s"]).fit([], {"s": []})


def test_shape_features():
    f = shape_features(["Return JSON for 2026-01-02 with 3 items?"])[0]
    assert f[1] == 4 and f[4] == 1.0 and f[5] == 1.0 and f[3] == 1


def test_hopeless_requests_do_not_buy_the_big_model():
    assert pick({"s": 0.03, "m": 0.05, "l": 0.1}, ALLOWED, 0.7) == "s"
    assert pick({"s": 0.03, "m": 0.05, "l": 0.3}, ALLOWED, 0.7) == "l"
