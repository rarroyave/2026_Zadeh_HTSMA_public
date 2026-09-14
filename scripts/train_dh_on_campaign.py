#!/usr/bin/env python3
"""
Supplementary analysis (not reported in the manuscript): how well can the
transformation enthalpy DeltaH be predicted from the campaign's own
measurements?

The script trains simple models on the second-cycle DSC enthalpies of the
transforming alloys in the Supplementary Information and compares them with
the DeltaH predictions the campaign actually used ('Predicted Enthalpy (J/g)').
Those came from a CatBoost model trained on a larger literature dataset that
is not part of this repository.

Models
    baseline   predict the training-set mean
    ridge      ridge regression on the seven at.% values
    cb_comp    CatBoost (MAE loss, default settings) on the seven at.% values
    cb_sina6   CatBoost (MAE loss, default settings) on the six descriptors
               selected in vendored/NiTi-alloy-discovery/ML models/main.ipynb

Evaluation
    repeated 5-fold cross-validation, grouped by composition, and a
    forward-in-time split (Iteration 1 -> 2, Iterations 1+2 -> 3)

Usage:  python train_dh_on_campaign.py [--data path] [--repeats 10] [--out DIR]
Requires catboost and scikit-learn (see requirements-ml.txt) and HEACalculator 1.3.0.
"""
import argparse
import contextlib
import importlib
import io
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from compute_spearman_mae import load_dsc_dataframe  # noqa: E402

ML_MODELS_DIR = REPO / "vendored" / "NiTi-alloy-discovery" / "ML models"
SINA6 = [
    "mat2vec_dev_33", "mat2vec_dev_48", "mat2vec_dev_92", "onehot_max_115",
    "comb_Cu/Co+Cu-Hf+Ni-Ti-Zr", "comb_Hf/Co-Cu-Ni+Pd+Ti+Zr",
]
ORDER = ["Ni", "Ti", "Cu", "Co", "Pd", "Hf", "Zr"]  # element order of comp_key in the loader
ALPHA = sorted(ORDER)  # column order used for the descriptor names above
MODEL_NAMES = ["baseline", "ridge", "cb_comp", "cb_sina6"]


def _feature_generator():
    """Import FeatureGenerator from the vendored ML-models helper.

    Evict any cached ``helper`` module first, since compute_lambda2_eps_tr.py
    imports a different helper.py under the same name.
    """
    sys.modules.pop("helper", None)
    sys.path.insert(0, str(ML_MODELS_DIR))
    try:
        return importlib.import_module("helper").FeatureGenerator
    finally:
        sys.path.pop(0)


def load(data_path):
    df = load_dsc_dataframe(Path(data_path))
    df = df[(df["Transforms"] == 1) & (df["Average Enthalpy (J/g)"] > 0)].reset_index(drop=True)
    comp = pd.DataFrame(df["comp_key"].str.split("|").tolist(), columns=ORDER).astype(float)
    return df, comp


def sina6_descriptors(comp):
    FeatureGenerator = _feature_generator()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        logging.getLogger().setLevel(logging.CRITICAL)
        fg = FeatureGenerator(comp[ALPHA])
        fg.generate_composition_formula()
        feats = fg.generate_features_all(main_elements=ALPHA)
    feats = feats.replace([np.inf, -np.inf], np.nan)
    present = [f for f in SINA6 if f in feats.columns]
    return feats[present].astype(float).to_numpy(), len(present)


def fit_predict(name, x_train, y_train, x_test):
    if name == "baseline":
        return np.full(len(x_test), y_train.mean())
    if name == "ridge":
        model = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-3, 3, 25)))
        return model.fit(x_train, y_train).predict(x_test)
    import catboost as cb
    model = cb.CatBoostRegressor(loss_function="MAE", silent=True, random_seed=0, thread_count=4,
                                 allow_writing_files=False)
    return model.fit(x_train, y_train).predict(x_test)


def metrics(y_true, y_pred):
    err = y_pred - y_true
    ss = ((y_true - y_true.mean()) ** 2).sum()
    rho = spearmanr(y_true, y_pred).statistic if np.ptp(y_pred) > 0 else np.nan
    return {
        "MAE": float(np.abs(err).mean()),
        "RMSE": float(np.sqrt((err ** 2).mean())),
        "R2": float(1 - (err ** 2).sum() / ss),
        "rho": float(rho),
    }


def run(data_path, repeats=10, seed=42):
    df, comp = load(data_path)
    y = df["Average Enthalpy (J/g)"].to_numpy()
    iteration = df["Iteration"].to_numpy()
    campaign = df["Predicted Enthalpy (J/g)"].to_numpy()
    groups = comp.round(3).astype(str).agg("|".join, axis=1).to_numpy()
    x_comp = comp[ORDER].to_numpy()
    x_sina, n_present = sina6_descriptors(comp)
    features = {"baseline": x_comp, "ridge": x_comp, "cb_comp": x_comp, "cb_sina6": x_sina}

    rng = np.random.default_rng(seed)
    unique_groups = np.array(sorted(set(groups)))
    rows, oof = [], {}
    for rep in range(repeats):
        fold_of = {g: i % 5 for i, g in enumerate(rng.permutation(unique_groups))}
        folds = np.array([fold_of[g] for g in groups])
        for name in MODEL_NAMES:
            pred = np.empty(len(y))
            for k in range(5):
                tr, te = folds != k, folds == k
                pred[te] = fit_predict(name, features[name][tr], y[tr], features[name][te])
            rows.append({"model": name, "repeat": rep, **metrics(y, pred)})
            oof[name] = pred
    cv = pd.DataFrame(rows).groupby("model")[["MAE", "RMSE", "R2", "rho"]].agg(["mean", "std"]).loc[MODEL_NAMES]

    mask = ~np.isnan(campaign)
    campaign_metrics = metrics(y[mask], campaign[mask])

    forward = []
    for train_its, test_it in [((1,), 2), ((1, 2), 3)]:
        tr, te = np.isin(iteration, train_its), iteration == test_it
        for name in MODEL_NAMES:
            forward.append({"train": "+".join(map(str, train_its)), "test": test_it, "model": name,
                            **metrics(y[te], fit_predict(name, features[name][tr], y[tr], features[name][te]))})
        forward.append({"train": "+".join(map(str, train_its)), "test": test_it, "model": "campaign",
                        **metrics(y[te & mask], campaign[te & mask])})

    return {
        "n": len(y),
        "per_iteration": {int(k): int(v) for k, v in pd.Series(iteration).value_counts().sort_index().items()},
        "sina6_present": n_present,
        "cv": cv,
        "campaign": campaign_metrics,
        "forward": pd.DataFrame(forward),
        "oof": pd.DataFrame({"iteration": iteration, "measured": y, "campaign_pred": campaign,
                             **{f"oof_{k}": v for k, v in oof.items()}}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default=str(REPO / "data" / "supplementary_data.xlsx"))
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--out", default=None, help="optional directory for CSV outputs and a parity plot")
    args = parser.parse_args()

    res = run(args.data, repeats=args.repeats)
    print(f"alloys: {res['n']} per iteration {res['per_iteration']}; Sina's descriptors present: {res['sina6_present']}/6")
    print(f"\n{args.repeats}x repeated 5-fold CV, grouped by composition (mean over repeats)")
    for name in MODEL_NAMES:
        r = res["cv"].loc[name]
        print(f"  {name:9s} MAE {r[('MAE', 'mean')]:5.2f}  RMSE {r[('RMSE', 'mean')]:5.2f}  "
              f"R2 {r[('R2', 'mean')]:6.2f}  rho {r[('rho', 'mean')]:5.2f}")
    c = res["campaign"]
    print(f"  campaign  MAE {c['MAE']:5.2f}  RMSE {c['RMSE']:5.2f}  R2 {c['R2']:6.2f}  rho {c['rho']:5.2f}  (predictions used in the campaign)")
    print("\nforward in time")
    with pd.option_context("display.width", 160):
        print(res["forward"].to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        res["cv"].to_csv(out / "dh_cv_metrics.csv")
        res["forward"].to_csv(out / "dh_forward_metrics.csv", index=False)
        res["oof"].to_csv(out / "dh_oof_predictions.csv", index=False)
        print(f"\nwrote CSV outputs to {out}")


if __name__ == "__main__":
    main()
