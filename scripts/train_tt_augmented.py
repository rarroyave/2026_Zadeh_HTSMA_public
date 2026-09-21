#!/usr/bin/env python3
"""Transformation temperatures (Ms, Mf, As, Af) with the campaign data added.

The vendored CatBoost-SMAs model is trained on 1,811 literature records that
are exclusively ternary and quaternary NiTi alloys. Every alloy in this
campaign has four to seven elements, so out of the box that model extrapolates
outside its training domain and its `family` categorical feature has never seen
any of these alloy families.

This module adds this campaign's own measured alloys to that training set and
refits, which is what the campaign itself did (Section 2.4.1: the surrogate was
retrained with the newly measured alloys appended after each iteration).

Measured out-of-sample accuracy, grouped 5-fold over the 81 campaign alloys
(train on the 1,689 literature records plus the other folds, predict the
held-out fold):

    target   literature-only      augmented
    Ms            69.2 C            48.5 C
    Mf            65.9 C            45.2 C
    As            96.1 C            59.5 C
    Af            96.0 C            62.4 C

Run this file directly to recompute these; it takes roughly 40 minutes
because each fit trains a CatBoost MultiRMSE model on ~3,100 features.

Two things to keep in mind if you edit this:

  * Roughly 53 C of error on Ms is large next to the -73 to +399 C span of the
    measured data. These models rank candidates, they do not predict pointwise,
    which is exactly how the manuscript uses them.

  * The campaign alloys were all homogenized at 950 C for 24 h, so that is the
    only processing condition the multi-principal-element part of the training
    set contains. Predictions at other schedules for these alloys are
    extrapolation, and `predict` warns when the default is used implicitly.

Nothing here is a stored model: the training data ships with the repository and
every prediction refits from it.

Usage:  python train_tt_augmented.py [--data path] [--folds 5] [--seed 0]
Requires catboost, scikit-learn and CBFV (see requirements.txt).
"""
from __future__ import annotations

import argparse
import warnings
from functools import reduce
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
VENDORED = REPO / "vendored" / "CatBoost-SMAs"
DATA = REPO / "data" / "supplementary_data.xlsx"

ELEM39 = ["Ag", "Al", "Au", "B", "Bi", "Ce", "Co", "Cr", "Cu", "Dy", "Er", "Fe", "Gd", "Hf",
          "In", "La", "Mn", "Mo", "Nb", "Nd", "Ni", "Pb", "Pd", "Pr", "Pt", "Re", "Rh", "Sb",
          "Sc", "Si", "Sn", "Ta", "Te", "Ti", "Tl", "V", "W", "Y", "Zr"]
PROC = ["Processing_BPHT_Temp", "Processing_BPHT_Time", "Processing_Rolling_Temp",
        "Processing_HR_Red", "Processing_CR_Red", "Processing_Extrusion_Temp",
        "Processing_Extrusion_Area_Reduction(%)", "Processing_APHT_Temp",
        "Processing_APHT_Time", "Processing_APHT_Method", "Processing_FinalHT_Temp",
        "Processing_FinalHT_Time", "Processing_FinalHT_Method"]
TARGETS = ["SME_Mf", "SME_Ms", "SME_As", "SME_Af"]
YCOLS = ["SME_Ms", "SME_Mf", "SME_As", "SME_Af"]        # the order main.py trains on
LABELS = ["Ms", "Mf", "As", "Af"]
CAT = ["family", "niti_bas", "nitihf_bas", "nitipd_bas", "niticu_bas", "nitinb_bas",
       "nitizr_bas", "nitib_bas"]

OURS = ["Ni", "Ti", "Cu", "Co", "Pd", "Hf", "Zr"]
COMP_COLS = [f"{e} (at.%)" for e in OURS]
MEAS = ["Ms (°C)", "Mf (°C)", "As (°C)", "Af (°C)"]

DEFAULT_HT_TEMP, DEFAULT_HT_TIME = 950.0, 24.0         # the campaign's schedule

# Arc-melted then solution treated: no thermomechanical processing at all. These
# are encoded explicitly rather than left blank, because CBFV median-imputes
# missing values and would otherwise invent typical rolled or extruded inputs.
NO_THERMOMECHANICAL = {
    "Processing_BPHT_Temp": 20.0, "Processing_BPHT_Time": 0.0,
    "Processing_Rolling_Temp": 20.0, "Processing_HR_Red": 0.0, "Processing_CR_Red": 0.0,
    "Processing_Extrusion_Temp": 20.0, "Processing_Extrusion_Area_Reduction(%)": 0.0,
    "Processing_APHT_Temp": 20.0, "Processing_APHT_Time": 0.0, "Processing_APHT_Method": 0.0,
    "Processing_FinalHT_Method": 0.0,
}

# Table B1 of the manuscript, as coded in vendored/CatBoost-SMAs/main.py.
PARAMS = {"learning_rate": 0.2092, "depth": 6, "l2_leaf_reg": 0.05992,
          "bagging_temperature": 0.5562, "loss_function": "MultiRMSE",
          "eval_metric": "MultiRMSE", "silent": True, "allow_writing_files": False}

# Out-of-sample MAE in deg C from the grouped 5-fold run described above. Quoted
# with every prediction so a number is never mistaken for a precise value.
CV_MAE = {"Ms": 48.5, "Mf": 45.2, "As": 59.5, "Af": 62.4}


# ----------------------------------------------------------------- training data
def literature_frame(vendored: Path = VENDORED) -> pd.DataFrame:
    """The 1,811 cleaned literature records, exactly as main.py selects them."""
    df = pd.read_csv(vendored / "raw_data.csv", engine="python")[
        [f"{e}(at%)" for e in ELEM39] + PROC + TARGETS]
    d = df[df.SME_Mf.notna() & df.SME_Ms.notna() & df.SME_As.notna()
           & df.SME_Af.notna()].drop_duplicates().reset_index(drop=True)
    d.columns = [c.replace("(at%)", "") for c in d.columns]
    d["Processing_CR_Red"] = d["Processing_CR_Red"].fillna(0)
    d = d[(d.SME_Af > d.SME_Ms) & (d.SME_Af > d.SME_As)
          & (d.SME_Ms > d.SME_Mf) & (d.SME_As > d.SME_Mf)].reset_index(drop=True)
    total = d[d.columns[:39]].sum(axis=1)
    return d[(total < 100.5) & (total > 99.5)].reset_index(drop=True)


def campaign_frame(data_path: Path = DATA) -> pd.DataFrame:
    """This campaign's transforming alloys, in the literature table's schema.

    Measured temperatures are read from the second DSC cycle, which is the cycle
    the manuscript reports. Note that the *predicted* columns of the same sheet
    are NOT all on the cycle-2 row -- seven alloys carry them on the cycle-1 row
    instead -- so anything comparing against the campaign's own predictions must
    pick them up per alloy, as compute_spearman_mae.load_dsc_dataframe does.
    Filtering to cycle 2 first silently drops those seven.
    """
    x = pd.read_excel(data_path, sheet_name="All Compiled Data", header=39)
    x = x.loc[:, ~x.columns.astype(str).str.contains("Unnamed")]
    x = x[(x["DSC Cycle Number"] == 2) & (x["Transforms"] == 1)]
    x = x[x[MEAS].notna().all(axis=1)]
    x = x[(x["Af (°C)"] > x["Ms (°C)"]) & (x["Af (°C)"] > x["As (°C)"])
          & (x["Ms (°C)"] > x["Mf (°C)"]) & (x["As (°C)"] > x["Mf (°C)"])].reset_index(drop=True)
    rows = []
    for _, r in x.iterrows():
        row = {e: 0.0 for e in ELEM39}
        for el, col in zip(OURS, COMP_COLS):
            row[el] = float(r[col])
        row.update(NO_THERMOMECHANICAL)
        row["Processing_FinalHT_Temp"] = float(r["HomoHT_Temp"])
        row["Processing_FinalHT_Time"] = float(r["HomoHT_Time"])
        for tgt, col in zip(["SME_Ms", "SME_Mf", "SME_As", "SME_Af"], MEAS):
            row[tgt] = float(r[col])
        rows.append(row)
    return pd.DataFrame(rows)[ELEM39 + PROC + TARGETS]


def query_frame(compositions, ht_temp=DEFAULT_HT_TEMP, ht_time=DEFAULT_HT_TIME) -> pd.DataFrame:
    """Rows for alloys to predict. `compositions` is a list of {element: at.%}."""
    rows = []
    for comp in compositions:
        row = {e: float(comp.get(e, 0.0)) for e in ELEM39}
        row.update(NO_THERMOMECHANICAL)
        row["Processing_FinalHT_Temp"] = float(ht_temp)
        row["Processing_FinalHT_Time"] = float(ht_time)
        for t in TARGETS:
            row[t] = 0.0
        rows.append(row)
    return pd.DataFrame(rows)[ELEM39 + PROC + TARGETS]


# ------------------------------------------------- formula and categorical features
def _correct_ratios(values):
    def gcd(a, b):
        return a if abs(b) < 1e-9 else gcd(b, a % b)
    g = reduce(gcd, values)
    return [round(v / g) for v in values]


# main.py maps element-set strings onto canonical family names; reproduced verbatim.
_FAMILY_ALIASES = [
    ("AlNiTiZr", "NiTiZrAl"), ("NiRhTi", "NiTiRh"), ("CuNiPdTi", "NiTiPdCu"),
    ("NiPdPtTi", "NiTiPdPt"), ("NbNiTiZr", "NiTiNbZr"), ("HfNiTiZr", "NiTiHfZr"),
    ("NiPdTaTi", "NiTiPdTa"), ("CuNiTi", "NiTiCu"), ("NiPtTi", "NiTiPt"),
    ("HfNiTi", "NiTiHf"), ("AuCuNiTi", "NiTiCuAu"), ("AuNiTi", "NiTiAu"),
    ("BNiPdTi", "NiTiPdB"), ("BNiTiZr", "NiTiZrB"), ("CoCuNiTi", "NiTiCuCo"),
    ("CoInMnNi", "NiMnCoIn"), ("CoNiPdTi", "NiTiPdCo"), ("CuFeHfNiTi", "NiTiHfFeCu"),
    ("CuHfNiTi", "NiTiHfCu"), ("CuHfNiTiZr", "NiTiHfZrCu"), ("CuNbNiTi", "NiTiCuNb"),
    ("CuNiTiZr", "NiTiCuZr"), ("HfNiPdTi", "NiTiPdHf"), ("NbNiTi", "NiTiNb"),
    ("NiPdScTi", "NiTiPdSc"), ("NiPdTi", "NiTiPd"),
]


def to_formula_df(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the `formula`, `family` and *_bas columns the vendored model expects."""
    d = frame.iloc[:, 0:39].to_dict("split")
    formulae = []
    for i in range(len(d["data"])):
        alloy = {d["columns"][j]: d["data"][i][j] for j in range(39) if d["data"][i][j] != 0}
        ratios = _correct_ratios(list(alloy.values()))
        formulae.append("".join(k + str(v) for k, v in zip(alloy.keys(), ratios)))
    out = pd.DataFrame({"formula": formulae})
    out = pd.concat([out, frame.iloc[:, 39:].reset_index(drop=True)], axis=1)
    family = out.formula.replace(r"\d+", "", regex=True)
    for old, new in _FAMILY_ALIASES:
        family = family.replace(old, new)
    out["family"] = family
    has = lambda f, *els: "Yes" if all(e in f for e in els) else "No"  # noqa: E731
    out["niti_bas"] = out.family.apply(lambda f: has(f, "Ni", "Ti"))
    for tag, el in [("nitihf_bas", "Hf"), ("nitipd_bas", "Pd"), ("niticu_bas", "Cu"),
                    ("nitinb_bas", "Nb"), ("nitizr_bas", "Zr"), ("nitib_bas", "B")]:
        out[tag] = out.family.apply(lambda f, el=el: has(f, "Ni", "Ti", el))
    return out


def build_features(formula_frames: list[pd.DataFrame]) -> list[pd.DataFrame]:
    """CBFV composition features plus the processing and categorical columns.

    CBFV's own `extend_features=True` path ends by taking the median of every
    column to fill missing values. Under pandas 1.5 that defaulted to numeric
    columns only, so the text columns passed through untouched; pandas 2 raises
    instead, which is why vendored/CatBoost-SMAs/main.py cannot run under this
    repository's pinned pandas. Generating the composition features alone and
    reattaching the other columns here reproduces the pandas 1.5 behaviour
    exactly, and was checked against the upstream run recorded in
    vendored/CatBoost-SMAs/NOTICE.md (RMSE 24.8 / MAE 17.2 / R2 0.936 here
    versus 24.7 / 17.0 / 0.936 there).

    All frames are featurized in one pass so their columns line up exactly.
    """
    from CBFV import composition

    sizes = [len(f) for f in formula_frames]
    combined = pd.concat(formula_frames, ignore_index=True)
    src = combined.drop(columns=["SME_Ms", "SME_As", "SME_Af"]).rename({"SME_Mf": "target"}, axis=1)
    extra = [c for c in src.columns if c not in ("formula", "target")]
    X, _, _, skipped = composition.generate_features(
        src[["formula", "target"]], elem_prop="jarvis", extend_features=False, sum_feat=True)
    if len(skipped) or len(X) != len(src):
        raise RuntimeError(f"CBFV skipped {len(skipped)} formula(e); {len(X)} of {len(src)} featurized")
    X = pd.concat([X.reset_index(drop=True), src[extra].reset_index(drop=True)], axis=1)
    numeric = X.select_dtypes(include=[np.number]).columns
    X[numeric] = X[numeric].fillna(X[numeric].median())
    out, start = [], 0
    for n in sizes:
        out.append(X.iloc[start:start + n].reset_index(drop=True))
        start += n
    return out


# ------------------------------------------------------------------------ model
def fit(X: pd.DataFrame, y: np.ndarray, seed: int = 0):
    import catboost as cb
    model = cb.CatBoostRegressor(**PARAMS, random_seed=seed)
    model.fit(cb.Pool(X, label=y, cat_features=CAT))
    return model


def predict(compositions, data_path: Path = DATA, vendored: Path = VENDORED,
            ht_temp=DEFAULT_HT_TEMP, ht_time=DEFAULT_HT_TIME, seed: int = 0):
    """Fit on literature + campaign data and predict Ms, Mf, As and Af.

    Returns (DataFrame indexed by Ms/Mf/As/Af per alloy, notes) where `notes`
    lists any caveats that apply to this particular call.
    """
    notes = []
    if (float(ht_temp), float(ht_time)) != (DEFAULT_HT_TEMP, DEFAULT_HT_TIME):
        notes.append(f"processing set to {ht_temp:g} C / {ht_time:g} h; every "
                     f"multi-principal-element alloy in the training data was homogenized at "
                     f"{DEFAULT_HT_TEMP:g} C / {DEFAULT_HT_TIME:g} h, so this is an extrapolation")

    lit = to_formula_df(literature_frame(vendored))
    camp = to_formula_df(campaign_frame(data_path))
    # main.py holds out compositions that occur only once; keep that for the
    # literature part, and keep every campaign alloy since each is unique.
    lit_model = lit.groupby("formula").filter(lambda g: len(g) > 1).reset_index(drop=True)
    query = to_formula_df(query_frame(compositions, ht_temp, ht_time))

    X_lit, X_camp, X_q = build_features([lit_model, camp, query])
    X_train = pd.concat([X_lit, X_camp], ignore_index=True)
    y_train = np.vstack([lit_model[YCOLS].to_numpy(float), camp[YCOLS].to_numpy(float)])

    import catboost as cb
    model = fit(X_train, y_train, seed=seed)
    pred = model.predict(cb.Pool(X_q, cat_features=CAT))
    notes.append(f"trained on {len(X_lit)} literature records + {len(X_camp)} campaign alloys")
    return pd.DataFrame(pred, columns=LABELS), notes


# -------------------------------------------------------------------------- main
def cross_validate(data_path: Path = DATA, vendored: Path = VENDORED,
                   folds: int = 5, seed: int = 0) -> dict:
    """Grouped k-fold over the campaign alloys, literature always in training."""
    from sklearn.model_selection import KFold
    import catboost as cb

    lit = to_formula_df(literature_frame(vendored))
    camp = to_formula_df(campaign_frame(data_path))
    lit_model = lit.groupby("formula").filter(lambda g: len(g) > 1).reset_index(drop=True)
    X_lit, X_camp = build_features([lit_model, camp])
    y_lit = lit_model[YCOLS].to_numpy(float)
    y_camp = camp[YCOLS].to_numpy(float)

    lit_only = fit(X_lit, y_lit, seed=seed).predict(cb.Pool(X_camp, cat_features=CAT))

    augmented = np.zeros_like(y_camp)
    for train_idx, test_idx in KFold(n_splits=folds, shuffle=True, random_state=seed).split(X_camp):
        X = pd.concat([X_lit, X_camp.iloc[train_idx]], ignore_index=True)
        y = np.vstack([y_lit, y_camp[train_idx]])
        augmented[test_idx] = fit(X, y, seed=seed).predict(
            cb.Pool(X_camp.iloc[test_idx].reset_index(drop=True), cat_features=CAT))

    mae = lambda p: {lab: float(np.abs(p[:, j] - y_camp[:, j]).mean())  # noqa: E731
                     for j, lab in enumerate(LABELS)}
    return {"n_literature": len(X_lit), "n_campaign": len(X_camp),
            "literature_only": mae(lit_only), "augmented": mae(augmented)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--vendored", type=Path, default=VENDORED)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    res = cross_validate(args.data, args.vendored, folds=args.folds, seed=args.seed)
    print(f"literature records {res['n_literature']}, campaign alloys {res['n_campaign']}")
    print(f"\nout-of-sample MAE over the campaign alloys ({args.folds}-fold), deg C")
    print(f"  {'target':6s} {'literature-only':>16s} {'augmented':>12s}")
    for lab in LABELS:
        print(f"  {lab:6s} {res['literature_only'][lab]:16.1f} {res['augmented'][lab]:12.1f}")
    print("\nThese models rank candidates; they are not pointwise predictors. The "
          "measured Ms of these alloys spans -73 to +399 deg C.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
