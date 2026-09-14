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
    """Ball-James lambda_2 for the champion alloy Ni46Ti28Co2Pd2Hf22."""
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
    """Reproduce Table 5's cycle-2 rho_Ms progression."""
    from compute_spearman_mae import load_dsc_dataframe, summarize
    df = load_dsc_dataframe(REPO / "data" / "supplementary_data.xlsx")
    for iteration, target in EXPECTED["rho_Ms_by_iteration"].items():
        it = int(iteration.split()[-1])
        row = summarize(df[df["Iteration"] == it], iteration)
        assert row["rho_Ms"] == pytest.approx(target, abs=0.01)


def test_table_5_aggregate_metrics_use_second_dsc_cycle():
    """Reproduce aggregate cycle-2 correlations and MAEs in Table 5."""
    from compute_spearman_mae import load_dsc_dataframe, summarize
    df = load_dsc_dataframe(REPO / "data" / "supplementary_data.xlsx")
    row = summarize(df, "All (Iter 1--3)")
    for prop, target in EXPECTED["table5_rho_all"].items():
        assert row[f"rho_{prop}"] == pytest.approx(target, abs=0.001)
    for prop, target in EXPECTED["table5_mae_all"].items():
        assert row[f"mae_{prop}"] == pytest.approx(target, abs=0.001)


def test_four_pass_counts_use_second_cycle_stress_free_dsc():
    """Reproduce the 6/8/6 per-iteration and 20-alloy four-pass counts."""
    from compute_four_pass_rates import iteration_summary, load_data
    df = load_data(REPO / "data" / "supplementary_data.xlsx")
    observed = {}
    for iteration in (1, 2, 3):
        label = f"Iteration {iteration}"
        observed[label] = iteration_summary(df, iteration)["four_pass"]
    assert observed == EXPECTED["four_pass_by_iteration"]
    assert sum(observed.values()) == EXPECTED["four_pass_total"]
