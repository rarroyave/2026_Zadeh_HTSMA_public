"""Section 3 and Appendix A.6: per-iteration Pareto-front membership."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXPECTED = json.loads((Path(__file__).parent / "expected_values.json").read_text())["pareto_membership"]


@pytest.fixture(scope="module")
def result():
    from compute_pareto_membership import load_objectives, membership
    return membership(load_objectives(REPO / "data" / "supplementary_data.xlsx"))


def test_strain_tested_alloys_per_iteration(result):
    assert [result["tested"][k] for k in (1, 2, 3)] == EXPECTED["tested"]


def test_front_after_iteration_2(result):
    assert [result["front_after_iteration_2"][k] for k in (1, 2)] == EXPECTED["front_after_iteration_2"]


def test_final_front_by_iteration(result):
    assert [result["on_final_front"][k] for k in (1, 2, 3)] == EXPECTED["on_final_front"]


def test_earlier_front_alloys_displaced(result):
    assert result["displaced_by_iteration_3"] == EXPECTED["displaced_by_iteration_3"]


def test_tail_probability(result):
    assert result["tail_probability"] == pytest.approx(EXPECTED["tail_probability"], abs=5e-4)
