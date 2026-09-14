"""The HEACalculator compatibility layer reproduces the values used in the study."""

import filecmp
import importlib
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
COMPAT_DIRS = [
    REPO / "vendored" / "Phase-Compatibility-Model-NiTi",
    REPO / "vendored" / "NiTi-alloy-discovery" / "ML models",
]

# Output of get_csv_list() from the HEACalculator 1.3.1 copy bundled in
# sinazadeh/NiTi-alloy-discovery@2e5ef7a: formula, density, atomic size
# difference, omega, gamma, lambda, VEC, mixing enthalpy, mixing entropy,
# melting temperature.
EXPECTED = {
    "Ni50Ti50": ["Ni50Ti50", "6.20", "8.49", "0.30", "1.20", "0.08", "7.00", "-35.00", "5.76", "1830.00"],
    "Ni46Ti28Co2Pd2Hf22": ["Ni46Ti28Co2Pd2Hf22", "8.91", "10.55", "0.50", "1.31", "0.09", "7.02", "-39.14", "10.00", "1958.00"],
    "Ni36Ti23Cu5Co2Pd7Hf19Zr8": ["Ni36Ti23Cu5Co2Pd7Hf19Zr8", "8.84", "10.51", "0.63", "1.32", "0.12", "7.17", "-41.84", "13.62", "1943.00"],
    "Ni49Ti29Co1Hf21": ["Ni49Ti29Co1Hf21", "8.74", "10.59", "0.46", "1.31", "0.08", "6.99", "-37.80", "9.00", "1950.00"],
}


def _load_compat(directory):
    sys.modules.pop("heacalc_compat", None)
    sys.path.insert(0, str(directory))
    try:
        return importlib.import_module("heacalc_compat")
    finally:
        sys.path.pop(0)


def test_compat_copies_are_identical():
    assert filecmp.cmp(COMPAT_DIRS[0] / "heacalc_compat.py", COMPAT_DIRS[1] / "heacalc_compat.py", shallow=False)


@pytest.mark.parametrize("formula", sorted(EXPECTED))
def test_csv_list_matches_study_copy(formula):
    compat = _load_compat(COMPAT_DIRS[0])
    assert compat.HEACalculator(formula, csv=True).get_csv_list() == EXPECTED[formula]
