#!/usr/bin/env python3
"""
Reproduce the predicted-vs-measured Spearman rank correlations and mean
absolute errors reported in Section 3 (Table 5 and surrounding discussion) of

    Zadeh et al., "Bayesian-Optimization-Guided Discovery of
    NiTi(Co,Cu,Pd,Hf,Zr) Multi-Principal Element High-Temperature Shape
    Memory Alloys", Acta Materialia (2026, submitted).

Input:  the manuscript's Supplementary Information Excel workbook
        (data/supplementary_data.xlsx by default).

Output: a tab-separated table of Spearman rho and MAE for M_s, A_f, DeltaT,
        DeltaH, computed per iteration and for the aggregate transforming
        subset. Numbers should reproduce those quoted in the manuscript.

Usage:  python compute_spearman_mae.py [--data path/to/supplementary_data.xlsx]
"""
import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

COMP_COLS = [
    "Ni (at.%)", "Ti (at.%)", "Cu (at.%)", "Co (at.%)",
    "Pd (at.%)", "Hf (at.%)", "Zr (at.%)",
]


def load_dsc_dataframe(path: Path) -> pd.DataFrame:
    """Load 'All Compiled Data' sheet and deduplicate to one row per alloy
    per iteration (max over multiple DSC cycles)."""
    df = pd.read_excel(path, sheet_name="All Compiled Data", header=39)
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed")]
    df["comp_key"] = df[COMP_COLS].astype(str).agg("|".join, axis=1)
    grouped = df.groupby(["Iteration", "comp_key"]).agg(
        {
            "Transforms": "max",
            "Ms (°C)": "max",
            "Af (°C)": "max",
            "Average Enthalpy (J/g)": "max",
            "Predicted Ms (°C)": "first",
            "Predicted Af (°C)": "first",
            "Predicted Enthalpy (J/g)": "first",
        }
    ).reset_index()
    grouped["DT_meas"] = grouped["Af (°C)"] - grouped["Ms (°C)"]
    grouped["DT_pred"] = (
        grouped["Predicted Af (°C)"] - grouped["Predicted Ms (°C)"]
    )
    return grouped


def spearman(a: pd.Series, b: pd.Series):
    mask = a.notna() & b.notna()
    if mask.sum() < 3:
        return np.nan, np.nan, int(mask.sum())
    rho, pval = spearmanr(a[mask], b[mask])
    return float(rho), float(pval), int(mask.sum())


def mae(a: pd.Series, b: pd.Series):
    mask = a.notna() & b.notna()
    if mask.sum() == 0:
        return np.nan, 0
    return float((a[mask] - b[mask]).abs().mean()), int(mask.sum())


def summarize(df: pd.DataFrame, label: str) -> dict:
    trans = df[df["Transforms"] == 1]
    row = {"subset": label, "N_transforming": len(trans)}
    for prop_name, pred, meas in [
        ("Ms",  "Predicted Ms (°C)",       "Ms (°C)"),
        ("Af",  "Predicted Af (°C)",       "Af (°C)"),
        ("DT",  "DT_pred",                       "DT_meas"),
        ("DH",  "Predicted Enthalpy (J/g)",      "Average Enthalpy (J/g)"),
    ]:
        rho, pval, n_r = spearman(trans[pred], trans[meas])
        m, n_m = mae(trans[pred], trans[meas])
        row[f"rho_{prop_name}"] = rho
        row[f"p_{prop_name}"] = pval
        row[f"mae_{prop_name}"] = m
        row[f"n_{prop_name}"] = n_r
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        default=str(Path(__file__).resolve().parent.parent / "data" / "supplementary_data.xlsx"),
        help="Path to the supplementary data Excel workbook",
    )
    args = parser.parse_args()

    df = load_dsc_dataframe(Path(args.data))

    rows = [summarize(df[df["Iteration"] == it], f"Iteration {it}") for it in (1, 2, 3)]
    rows.append(summarize(df, "All (Iter 1--3)"))

    out = pd.DataFrame(rows)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(out.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()
