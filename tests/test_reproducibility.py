"""Regression tests. Verify the three reproduction scripts still emit the
numbers reported in Zadeh et al. 2026 within tolerance.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXPECTED = json.loads((Path(__file__).parent / "expected_values.json").read_text())


def test_champion_lambda2():
    """Ball-James lambda_2 for the champion alloy Ni46Ti28Hf22Pd2Co2."""
    from compute_lambda2_eps_tr import compute_lambdas
    pcm = REPO / "vendored" / "Phase-Compatibility-Model-NiTi"
    lam = compute_lambdas(pcm, EXPECTED["champion_lattice"])
    assert lam["lambda2"] == pytest.approx(EXPECTED["champion_lambda2"], abs=1e-4)


def test_champion_eps_tr_110_tension():
    """[1,1,0] tensile transformation strain for the champion alloy."""
    from compute_lambda2_eps_tr import compute_eps_tr
    tsm = REPO / "vendored" / "Transformation-Strain-Model-NiTi"
    eps = compute_eps_tr(tsm, EXPECTED["champion_lattice"])
    assert eps["[1, 1, 0]"]["tension_pct"] == pytest.approx(
        EXPECTED["champion_eps_tr_110_tension_pct"], abs=1e-2
    )


def test_supplementary_data_shape():
    """Aggregated SI must have exactly 87 unique (iteration, composition) rows."""
    from compute_spearman_mae import load_dsc_dataframe
    df = load_dsc_dataframe(REPO / "data" / "supplementary_data.xlsx")
    assert len(df) == EXPECTED["n_alloys_after_dedup"]


def test_rho_ms_progression_matches_table_5():
    """Reproduce Table 5's rho_Ms Iter 1 -> Iter 3 progression (0.25 -> 0.73)."""
    from compute_spearman_mae import load_dsc_dataframe, summarize
    df = load_dsc_dataframe(REPO / "data" / "supplementary_data.xlsx")
    for iteration, target in EXPECTED["rho_Ms_by_iteration"].items():
        it = int(iteration.split()[-1])
        row = summarize(df[df["Iteration"] == it], iteration)
        assert row["rho_Ms"] == pytest.approx(target, abs=0.01)
