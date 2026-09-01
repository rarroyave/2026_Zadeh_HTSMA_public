#!/usr/bin/env python3
"""
Reproduce the crystallographic-compatibility (lambda_1, lambda_2, lambda_3)
and theoretical transformation-strain (eps_tr) values for the champion alloy
Ni46Ti28Hf22Pd2Co2 (and the low-hysteresis reference alloy
Ni45Ti25Co5Hf11Zr14) reported in Section 3 of

    Zadeh et al., "Bayesian-Optimization-Guided Discovery of
    NiTi(Co,Cu,Pd,Hf,Zr) Multi-Principal Element High-Temperature Shape
    Memory Alloys", Acta Materialia (2026, submitted).

Uses the publicly-available models by S. Hossein Zadeh:

    Phase-Compatibility-Model-NiTi
      https://github.com/sinazadeh/Phase-Compatibility-Model-NiTi
    Transformation-Strain-Model-NiTi
      https://github.com/sinazadeh/Transformation-Strain-Model-NiTi

Both are vendored as git submodules under ``vendored/`` in this repo. After
``git clone --recursive`` (or ``git submodule update --init --recursive``),
the script finds them by default. Override with --pcm-dir / --tsm-dir to
point elsewhere.

Usage:
    python scripts/compute_lambda2_eps_tr.py
"""
import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Measured B2 and B19' lattice parameters (from Supplementary Information):
#   a0  = B2 austenite parameter (Angstrom)
#   a,b,c,beta = B19' martensite parameters
ALLOYS = {
    "Ni46Ti28Hf22Pd2Co2 (champion)": dict(
        a0=3.09013, a=3.09851, b=4.12942, c=4.90601, beta=103.046,
    ),
    "Ni45Ti25Co5Hf11Zr14 (lowest-DT)": dict(
        a0=3.10695, a=3.09751, b=4.09724, c=4.86795, beta=102.425,
    ),
}

DIRECTIONS = [[1, 0, 0], [1, 1, 0], [1, 1, 1], [0, 1, 1], [2, 1, 0]]


def _import_helper(helper_dir: Path):
    """Import the `helper` module from a specific directory, evicting any
    previously-cached `helper` from sys.modules so PCM and TSM helpers can
    coexist within one Python process."""
    import importlib
    sys.modules.pop("helper", None)
    sys.path.insert(0, str(helper_dir))
    helper = importlib.import_module("helper")
    sys.path.pop(0)
    return helper


def compute_lambdas(pcm_dir: Path, alloy_data: dict) -> dict:
    helper = _import_helper(pcm_dir)

    df = helper.DataHandler(
        {
            "a0 (A)": [alloy_data["a0"]],
            "a (A)": [alloy_data["a"]],
            "b (A)": [alloy_data["b"]],
            "c (A)": [alloy_data["c"]],
            "beta": [alloy_data["beta"]],
        }
    ).generate_dataframe()
    lam = helper.LambdaCalculator(df).generate_lambdas().iloc[0]
    return {
        "lambda1": float(lam["lambda1_calculated"]),
        "lambda2": float(lam["lambda2_calculated"]),
        "lambda3": float(lam["lambda3_calculated"]),
    }


def compute_eps_tr(tsm_dir: Path, alloy_data: dict) -> dict:
    helper = _import_helper(tsm_dir)

    calc = helper.TransformationStrainCalculator()
    calc.set_lattice_constants_and_beta(
        alloy_data["a0"], alloy_data["a"], alloy_data["b"], alloy_data["c"], alloy_data["beta"]
    )
    results = {}
    for d in DIRECTIONS:
        calc.set_custom_directions(d)
        info = calc.calc_max_strain_and_info()
        # info[0] = (tens_pct, comp_pct, direction); values already in percent.
        results[str(d)] = {"tension_pct": float(info[0][0]), "compression_pct": float(info[0][1])}
    return results


def main() -> None:
    here = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pcm-dir", default=str(here / "vendored" / "Phase-Compatibility-Model-NiTi"),
                   help="Path to Phase-Compatibility-Model-NiTi clone")
    p.add_argument("--tsm-dir", default=str(here / "vendored" / "Transformation-Strain-Model-NiTi"),
                   help="Path to Transformation-Strain-Model-NiTi clone")
    args = p.parse_args()

    pcm = Path(args.pcm_dir).expanduser().resolve()
    tsm = Path(args.tsm_dir).expanduser().resolve()

    for label, data in ALLOYS.items():
        print("=" * 72)
        print(label)
        print("=" * 72)
        lam = compute_lambdas(pcm, data)
        print(f"  lambda1 = {lam['lambda1']:.4f}   lambda2 = {lam['lambda2']:.4f}   lambda3 = {lam['lambda3']:.4f}")
        print("  Theoretical single-crystal transformation strain (percent):")
        eps = compute_eps_tr(tsm, data)
        print(f"    {'Direction':<12} {'Tension':>10} {'Compression':>14}")
        for d, e in eps.items():
            print(f"    {d:<12} {e['tension_pct']:>10.3f} {e['compression_pct']:>14.3f}")
        print()


if __name__ == "__main__":
    main()
