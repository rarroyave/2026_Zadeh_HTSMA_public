#!/usr/bin/env python3
"""
Reproduce the per-iteration Pareto-front membership reported in Section 3 and
Appendix A.6 of

    Zadeh et al., "Bayesian-Optimization-Guided Discovery of
    NiTi(Co,Cu,Pd,Hf,Zr) Multi-Principal Element High-Temperature Shape
    Memory Alloys", Acta Materialia (2026, in review).

Objective space (-DeltaT, DeltaH, eps_tr), all maximized, over the 31
strain-tested alloys:

    DeltaT  midpoint hysteresis A50 - M50 = (A_s + A_f)/2 - (M_s + M_f)/2,
            second DSC cycle
    DeltaH  average transformation enthalpy, second DSC cycle
    eps_tr  largest transformation strain measured under UCFTC

The script reports the cumulative Pareto front after each iteration, the
per-iteration contribution to the final front, the number of earlier front
alloys dominated by Iteration 3, and the binomial tail probability of the
Iteration 3 count under a baseline calibrated on the Iteration 1 rate.

Usage:  python compute_pareto_membership.py [--data path/to/supplementary_data.xlsx]
"""
import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

from compute_four_pass_rates import COMP_COLS, load_data

warnings.filterwarnings("ignore")


def load_objectives(path: Path) -> pd.DataFrame:
    """One row per strain-tested alloy with the three objectives."""
    dsc = pd.read_excel(path, sheet_name="All Compiled Data", header=39)
    dsc = dsc.loc[:, ~dsc.columns.astype(str).str.contains("Unnamed")]
    dsc = dsc[dsc["DSC Cycle Number"] == 2].copy()
    dsc["comp_key"] = dsc[COMP_COLS].astype(str).agg("|".join, axis=1)
    dsc["DT_mid"] = (dsc["As (°C)"] + dsc["Af (°C)"]) / 2 - (dsc["Ms (°C)"] + dsc["Mf (°C)"]) / 2
    peak = load_data(path)[["Iteration", "comp_key", "eps_peak"]]
    df = dsc.merge(peak, on=["Iteration", "comp_key"], how="inner")
    df = df.rename(columns={"Average Enthalpy (J/g)": "DH"})
    return df.dropna(subset=["DT_mid", "DH", "eps_peak"]).reset_index(drop=True)


def pareto_front(y: np.ndarray) -> np.ndarray:
    """Indices of non-dominated rows (all objectives maximized)."""
    keep = []
    for i in range(len(y)):
        dominated = np.any(np.all(y >= y[i], axis=1) & np.any(y > y[i], axis=1))
        if not dominated:
            keep.append(i)
    return np.array(keep, dtype=int)


def membership(df: pd.DataFrame) -> dict:
    y = np.column_stack([-df["DT_mid"], df["DH"], df["eps_peak"]])
    it = df["Iteration"].to_numpy()
    tested = {k: int((it == k).sum()) for k in (1, 2, 3)}

    after2 = np.flatnonzero(it <= 2)[pareto_front(y[it <= 2])]
    final = pareto_front(y)
    on_final = {k: int((it[final] == k).sum()) for k in (1, 2, 3)}
    rate = {k: on_final[k] / tested[k] for k in (1, 2, 3)}
    displaced = len(after2) - int(np.isin(after2, final).sum())
    tail = float(binom.sf(on_final[3] - 1, tested[3], rate[1]))
    return {
        "tested": tested,
        "front_after_iteration_2": {k: int((it[after2] == k).sum()) for k in (1, 2)},
        "on_final_front": on_final,
        "rate": rate,
        "displaced_by_iteration_3": displaced,
        "tail_probability": tail,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=str(Path(__file__).resolve().parent.parent / "data" / "supplementary_data.xlsx"))
    args = p.parse_args()

    r = membership(load_objectives(Path(args.data)))
    a2 = r["front_after_iteration_2"]
    print(f"Strain-tested alloys (Iterations 1/2/3): {r['tested'][1]}/{r['tested'][2]}/{r['tested'][3]}")
    print(f"Pareto front after Iteration 2: {sum(a2.values())} alloys ({a2[1]} from Iteration 1, {a2[2]} from Iteration 2)")
    print(f"Final Pareto front: {sum(r['on_final_front'].values())} alloys")
    print(f"  {'Iteration':<10}{'tested':>8}{'on front':>10}{'rate':>7}")
    for k in (1, 2, 3):
        print(f"  {k:<10}{r['tested'][k]:>8}{r['on_final_front'][k]:>10}{r['rate'][k]:>7.2f}")
    print(f"Earlier front alloys dominated by Iteration 3 alloys: {r['displaced_by_iteration_3']}")
    k, n, p1 = r["on_final_front"][3], r["tested"][3], r["rate"][1]
    print(f"Pr(Z >= {k} | Z ~ Binomial({n}, {p1:.2f})) = {r['tail_probability']:.3f}")


if __name__ == "__main__":
    main()
