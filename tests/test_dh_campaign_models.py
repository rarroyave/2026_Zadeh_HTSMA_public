"""Supplementary DeltaH analysis runs and behaves as documented in the README."""

import importlib
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("catboost")
pytest.importorskip("sklearn")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def test_dh_models_trained_on_campaign_data():
    module = importlib.import_module("train_dh_on_campaign")
    res = module.run(REPO / "data" / "supplementary_data.xlsx", repeats=2)
    expected = json.loads((REPO / "tests" / "expected_values.json").read_text())

    assert res["n"] == 72
    assert res["per_iteration"] == {1: 23, 2: 23, 3: 26}
    assert res["sina6_present"] == 6
    # The campaign's own predictions reproduce the Table 5 DeltaH MAE.
    assert res["campaign"]["MAE"] == pytest.approx(expected["table5_mae_all"]["DH"], abs=0.01)
    cv = res["cv"]
    baseline = cv.loc["baseline", ("MAE", "mean")]
    assert cv.loc["ridge", ("MAE", "mean")] < baseline
    assert cv.loc["cb_comp", ("MAE", "mean")] < baseline
