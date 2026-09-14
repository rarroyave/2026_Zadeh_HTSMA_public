#!/usr/bin/env python3
"""
Reproduce the per-iteration hit rates against the four functional targets
    M_s in [200, 400] deg C
    DeltaT = A_f - M_s <= 50 deg C (second-cycle, stress-free DSC)
    DeltaH >= 20 J/g
    eps_tr >= 2.5 % (measured under UCFTC)
reported in Section 3 and Appendix A.

The joint 4-pass rate (6/29 = 21%) in Iteration 1 is the calibration point
used for the CALPHAD/BO attribution analysis in Section 3.

Usage:  python compute_four_pass_rates.py [--data path/to/supplementary_data.xlsx]
"""
import argparse
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

COMP_COLS = [
    "Ni (at.%)", "Ti (at.%)", "Cu (at.%)", "Co (at.%)",
    "Pd (at.%)", "Hf (at.%)", "Zr (at.%)",
]


def load_data(path: Path):
    dsc = pd.read_excel(path, sheet_name="All Compiled Data", header=39)
    dsc = dsc.loc[:, ~dsc.columns.astype(str).str.contains("Unnamed")]
    dsc = dsc[dsc["DSC Cycle Number"] == 2].copy()
    dsc["comp_key"] = dsc[COMP_COLS].astype(str).agg("|".join, axis=1)
    dsc = dsc[
        [
            "Iteration", "comp_key", "Transforms", "Ms (°C)", "Af (°C)",
            "Average Enthalpy (J/g)",
        ]
    ]
    dsc["DT_DSC"] = dsc["Af (°C)"] - dsc["Ms (°C)"]

    ucftc_frames = []
    for sheet in ["Iteration 1 UCFTC", "Iteration 2 UCFTC", "Iteration 3 UCFTC"]:
        d = pd.read_excel(path, sheet_name=sheet, header=40)
        d = d.loc[:, ~d.columns.astype(str).str.contains("Unnamed")]
        ucftc_frames.append(d)
    ucftc = pd.concat(ucftc_frames, ignore_index=True)
    ucftc["comp_key"] = ucftc[COMP_COLS].astype(str).agg("|".join, axis=1)

    peak = ucftc.groupby(["Iteration", "comp_key"])["Epsilon_Transformation"].max().reset_index()
    peak.rename(columns={"Epsilon_Transformation": "eps_peak"}, inplace=True)

    merged = dsc.merge(peak, on=["Iteration", "comp_key"], how="left")
    return merged


def iteration_summary(merged: pd.DataFrame, iteration: int) -> dict[str, int]:
    """Return target-hit counts for one 29-alloy iteration."""
    sub = merged[merged["Iteration"] == iteration]
    trans = sub[sub["Transforms"] == 1]
    ms_mask = (trans["Ms (°C)"] >= 200) & (trans["Ms (°C)"] <= 400)
    dt_mask = (trans["DT_DSC"] <= 50) & trans["DT_DSC"].notna()
    dh_mask = trans["Average Enthalpy (J/g)"] >= 20
    eps_mask = trans["eps_peak"] >= 2.5
    return {
        "n": len(sub),
        "transforms": int(trans["Transforms"].sum()),
        "ms_hit": int(ms_mask.sum()),
        "dt_hit": int(dt_mask.sum()),
        "dh_hit": int(dh_mask.sum()),
        "eps_hit": int(eps_mask.sum()),
        "four_pass": int((ms_mask & dt_mask & dh_mask & eps_mask).sum()),
    }


def summarize(merged: pd.DataFrame):
    print(f"{'Iter':<6} {'N':<4} {'trans':<8} {'Ms hit':<12} {'DT hit':<12} {'DH hit':<12} {'eps hit':<12} {'4-pass':<12}")
    print("-" * 80)
    for it in (1, 2, 3):
        row = iteration_summary(merged, it)
        n = row["n"]
        print(
            f"{it:<6} {n:<4} {row['transforms']}/{n:<6} "
            f"{row['ms_hit']}/{n} ({100*row['ms_hit']/n:>3.0f}%)  "
            f"{row['dt_hit']}/{n} ({100*row['dt_hit']/n:>3.0f}%)  "
            f"{row['dh_hit']}/{n} ({100*row['dh_hit']/n:>3.0f}%)  "
            f"{row['eps_hit']}/{n} ({100*row['eps_hit']/n:>3.0f}%)  "
            f"{row['four_pass']}/{n} ({100*row['four_pass']/n:>3.0f}%)"
        )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--data",
        default=str(Path(__file__).resolve().parent.parent / "data" / "supplementary_data.xlsx"),
    )
    args = p.parse_args()
    merged = load_data(Path(args.data))
    summarize(merged)


if __name__ == "__main__":
    main()
