#!/usr/bin/env python3
"""
Regenerate the 3,812,408-row candidate composition space used by the
Probability_calculations sub-pipeline of the Bayesian-optimization campaign.

The design space is a regular grid over seven elements (Ni, Ti, Cu, Hf, Zr,
Pd, Co --- the column order used in `all_space.csv`), all in atomic percent,
filtered by:

    Ni  in [20.0, 51.5]  step 0.2      (Ni/Ti finer grid captures the
    Ti  in [20.0, 50.0]  step 0.2       near-stoichiometric sensitivity)
    Cu  == 0  or  in [5, 25]  step 1   (below 5 at.% skipped --- dilute
    Hf  == 0  or  in [5, 25]  step 1    substitution has no measurable
    Zr  == 0  or  in [5, 25]  step 1    effect on transformation behaviour)
    Pd  in [0, 25]        step 1
    Co  in [0,  5]        step 1

plus four joint constraints:

    Ni + Ti + Cu + Hf + Zr + Pd + Co == 100          (composition closure)
    Ni-site sum (Ni + Cu + Co + Pd) in [50.0, 51.4]  (Ni-rich by 0 to 1.4 at.%)
    Ti-site sum (Ti + Hf + Zr)      in [48.6, 50.0]  (= 100 - Ni-site)
    at least 2 of {Cu, Hf, Zr, Pd, Co} > 0           (multi-principal-element:
                                                      quaternary minimum, no
                                                      ternary alloys)

Column order in `all_space.csv`: Ni, Ti, Cu, Hf, Zr, Pd, Co
(from the `# The order of elements` comment in `Iter2/main.py`).

Reference:  Zadeh Ph.D. dissertation, Section 4.2.3 "Design Space Definition"
            Broucek Ph.D. dissertation, Section 8.2.2

The output CSV is the file that `Iter2/Probability_calculations/itr2/main.py`
and `Iter3/Probability_calculations/itr3/main.py` read as ``all_space.csv``
(the same enumeration is used for both iterations). We ship this generator
instead of the raw CSV (~128 MB) because the CSV is runtime-derivable at
~30 s cost and would bloat every clone of this repository.

Usage:
    python generate_design_space.py > Iter2/Probability_calculations/itr2/all_space.csv
    python generate_design_space.py > Iter3/Probability_calculations/itr3/all_space.csv

Or, from either Probability_calculations subdirectory:
    python ../../generate_design_space.py > all_space.csv

The enumeration is done in integer arithmetic (multiplied by 5 so 0.2 at.%
becomes 1 unit) to avoid floating-point drift when checking sum == 100.
"""
from __future__ import annotations

import argparse
import sys

# Scale factor: 1 integer unit = 0.2 at.%.
S = 5
TARGET = 100 * S  # 500

# --- Per-element ranges (integer units of 0.2 at.%) ------------------------

# Ni: 20.0 to 51.4 at.% in 0.2 at.% steps (max 51.4 = floor of 51.5 at 0.2 step from 20)
NI = list(range(20 * S, int(51.5 * S) + 1))     # 100..257  (158 values)
# Ti: 20.0 to 50.0 at.% in 0.2 at.% steps
TI = list(range(20 * S, 50 * S + 1))             # 100..250  (151 values)
TI_SET = set(TI)
# Cu, Hf, Zr: 0 at.% or 5..25 at.% in 1 at.% steps
CU = [0] + list(range(5 * S, 26 * S, S))         # 0, 25, 30, ..., 125  (22 values)
HF = list(CU)
ZR = list(CU)
# Pd: 0..25 at.% in 1 at.% steps (continuous)
PD = list(range(0, 26 * S, S))                   # 0, 5, 10, ..., 125   (26 values)
# Co: 0..5 at.% in 1 at.% steps
CO = list(range(0, 6 * S, S))                    # 0, 5, 10, 15, 20, 25 (6 values)

# --- Sublattice bounds (Ni-rich by 0 to 1.4 at.%) --------------------------

NI_SITE_MIN = 50 * S                             # 250 (= 50.0 at.%)
NI_SITE_MAX = int(51.4 * S)                      # 257 (= 51.4 at.%)


def format_scaled(v: int) -> str:
    """Format an integer scaled value (units of 0.2 at.%) as an at.% string."""
    if v % S == 0:
        return f"{v // S}.0"
    return f"{v / S:.1f}"


def emit(row: tuple[int, ...], out) -> None:
    out.write(",".join(format_scaled(x) for x in row))
    out.write("\n")


def generate(out=sys.stdout, count_only: bool = False) -> int:
    """Enumerate every valid composition. Returns the row count.

    Column order emitted: Ni, Ti, Cu, Hf, Zr, Pd, Co (matches Sina's
    all_space.csv).
    """
    n = 0
    # Outer loop: Ni-site substituents (Cu, Pd, Co). This lets us compute Ni
    # exactly from the fixed Ni-site sum, then enumerate Ti-site substituents.
    for cu in CU:
        for pd_val in PD:
            for co in CO:
                ni_site_others = cu + pd_val + co
                # Ni + ni_site_others must equal Ni-site sum in [MIN, MAX]
                ni_lo = max(20 * S, NI_SITE_MIN - ni_site_others)
                ni_hi = min(int(51.5 * S), NI_SITE_MAX - ni_site_others)
                if ni_lo > ni_hi:
                    continue
                for ni in range(ni_lo, ni_hi + 1):
                    ni_site = ni + ni_site_others            # in [250, 257]
                    ti_site = TARGET - ni_site                # in [243, 250]
                    for hf in HF:
                        for zr in ZR:
                            ti = ti_site - hf - zr
                            if ti not in TI_SET:
                                continue
                            # Multi-principal-element: at least 2 substituents nonzero
                            if sum(1 for x in (cu, hf, zr, pd_val, co) if x > 0) < 2:
                                continue
                            if not count_only:
                                emit((ni, ti, cu, hf, zr, pd_val, co), out)
                            n += 1
    return n


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--count-only", action="store_true",
                   help="Emit only the row count on stderr; suppress the CSV rows.")
    args = p.parse_args()
    n = generate(sys.stdout, count_only=args.count_only)
    if args.count_only:
        print(f"{n:,} rows", file=sys.stderr)
    else:
        print(f"# wrote {n:,} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
