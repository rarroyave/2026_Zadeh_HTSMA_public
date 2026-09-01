#!/usr/bin/env python3
"""
Reproduce the per-iteration hit rates against the four functional targets
    M_s in [200, 400] deg C
    DeltaT <= 50 deg C
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
    dsc["comp_key"] = dsc[COMP_COLS].astype(str).agg("|".join, axis=1)
    dsc = dsc.groupby(["Iteration", "comp_key"]).agg(
        {
            "Transforms": "max",
            "Ms (°C)": "max",
            "Af (°C)": "max",
            "Average Enthalpy (J/g)": "max",
        }
    ).reset_index()
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

    lowload = ucftc.loc[
        ucftc.groupby(["Iteration", "comp_key"])["Load (MPa)"].idxmin()
    ][["Iteration", "comp_key", "Load (MPa)", "Thermal Hysteresis (°C)"]]
    lowload.rename(columns={"Thermal Hysteresis (°C)": "DT_UCFTC"}, inplace=True)

    merged = dsc.merge(peak, on=["Iteration", "comp_key"], how="left")
    merged = merged.merge(
        lowload[["Iteration", "comp_key", "DT_UCFTC"]],
        on=["Iteration", "comp_key"],
        how="left",
    )
    return merged


def summarize(merged: pd.DataFrame):
    print(f"{'Iter':<6} {'N':<4} {'trans':<8} {'Ms hit':<12} {'DT hit':<12} {'DH hit':<12} {'eps hit':<12} {'4-pass':<12}")
    print("-" * 80)
    for it in (1, 2, 3):
        sub = merged[merged["Iteration"] == it]
        trans = sub[sub["Transforms"] == 1]
        n = len(sub)
        ms_hit = ((trans["Ms (°C)"] >= 200) & (trans["Ms (°C)"] <= 400)).sum()
        dt_hit = ((trans["DT_UCFTC"] <= 50) & trans["DT_UCFTC"].notna()).sum()
        dh_hit = (trans["Average Enthalpy (J/g)"] >= 20).sum()
        eps_hit = (trans["eps_peak"] >= 2.5).sum()
        four_pass = trans[
            (trans["Ms (°C)"] >= 200) & (trans["Ms (°C)"] <= 400)
            & (trans["DT_UCFTC"] <= 50) & trans["DT_UCFTC"].notna()
            & (trans["Average Enthalpy (J/g)"] >= 20)
            & (trans["eps_peak"] >= 2.5)
        ]
        print(
            f"{it:<6} {n:<4} {int(trans['Transforms'].sum())}/{n:<6} "
            f"{ms_hit}/{n} ({100*ms_hit/n:>3.0f}%)  "
            f"{dt_hit}/{n} ({100*dt_hit/n:>3.0f}%)  "
            f"{dh_hit}/{n} ({100*dh_hit/n:>3.0f}%)  "
            f"{eps_hit}/{n} ({100*eps_hit/n:>3.0f}%)  "
            f"{len(four_pass)}/{n} ({100*len(four_pass)/n:>3.0f}%)"
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
