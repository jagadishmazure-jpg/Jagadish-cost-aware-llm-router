import numpy as np
import pytest

from costroute.cost import VM_USD_PER_HOUR, CostModel
from costroute.metrics import auc, brier, percentile, rate, wilson


def test_cost_is_seconds_times_price():
    assert CostModel().usd(3600) == pytest.approx(VM_USD_PER_HOUR)
    assert CostModel(utilisation=0.5).usd(3600) == pytest.approx(2 * VM_USD_PER_HOUR)


def test_cost_inputs_checked():
    with pytest.raises(ValueError):
        CostModel(usd_per_hour=0)
    with pytest.raises(ValueError):
        CostModel(utilisation=1.5)
    with pytest.raises(ValueError):
        CostModel().usd(-1)


def test_wilson_known_values():
    lo, hi = wilson(0, 10)
    assert lo == 0 and hi == pytest.approx(0.2775, abs=1e-4)
    assert rate(5, 10)["ci95"] == [0.2366, 0.7634]
    with pytest.raises(ValueError):
        wilson(3, 0)


def test_percentile_and_brier():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert brier(np.array([1.0, 0.0]), np.array([1, 0])) == 0.0


def test_auc():
    y = np.array([0, 0, 1, 1])
    assert auc(np.array([0.1, 0.2, 0.8, 0.9]), y) == 1.0
    assert auc(np.array([0.5] * 4), y) == 0.5
    assert auc(np.array([0.1, 0.2]), np.array([1, 1])) is None
