"""Section 3 and Appendix A.7: the lambda_2 and LDT strain models compared with
values computed from the measured lattice parameters.

The strain comparison solves the lattice deformation matrices for every alloy
and takes a few minutes; the results are computed once per test session.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXPECTED = json.loads((Path(__file__).parent / "expected_values.json").read_text())["lattice_model_check"]


@pytest.fixture(scope="module")
def results():
    pytest.importorskip("catboost")
    from compare_lambda2_ldt_models import run
    return run(REPO / "data" / "supplementary_data.xlsx")


def test_alloys_with_measured_lattice_parameters(results):
    assert results["n_alloys"] == EXPECTED["n_alloys"]


def test_champion_measured_lambda2_matches_section_3(results):
    a = results["alloys"]
    champion = a[(a.Ni == 46) & (a.Ti == 28) & (a.Co == 2) & (a.Pd == 2) & (a.Hf == 22)]
    assert len(champion) == 1
    assert champion.lambda2_meas.iloc[0] == pytest.approx(0.9449, abs=1e-4)


def test_lambda2_model_against_measured_lambda2(results):
    m = results["lambda2"]
    assert m["rho"] == pytest.approx(EXPECTED["lambda2_rho"], abs=0.005)
    assert m["p"] < 1e-4
    assert m["mae"] == pytest.approx(EXPECTED["lambda2_mae"], abs=5e-4)


def test_measured_lambda2_against_dsc_hysteresis(results):
    m = results["lambda2_vs_dT"]
    assert m["rho"] == pytest.approx(EXPECTED["lambda2_vs_dT_rho"], abs=0.005)
    assert m["p"] < 1e-3


def test_ldt_strain_model_against_measured_lattice(results):
    # CatBoost results can differ slightly across versions and platforms.
    m = results["strain"]
    assert m["rho"] == pytest.approx(EXPECTED["strain_rho"], abs=0.02)
    assert m["mae"] == pytest.approx(EXPECTED["strain_mae_pct"], abs=0.15)


def test_every_alloy_passes_the_strain_screening_threshold(results):
    n = results["n_alloys"]
    assert results["n_above_threshold_meas"] == n
    assert results["n_above_threshold_pred"] == n
