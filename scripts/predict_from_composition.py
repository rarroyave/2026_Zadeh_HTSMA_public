#!/usr/bin/env python3
"""Predict alloy properties from composition alone.

Give a composition in the NiTi(Co,Cu,Pd,Hf,Zr) design space and this reports
the properties the campaign's composition-only models can estimate:

    lambda_2        crystallographic compatibility (middle eigenvalue)
    eps_tr          theoretical single-crystal transformation strain, %
    Delta H         transformation enthalpy, J/g
    Ms/Mf/As/Af     transformation temperatures, degC (--with-temperatures)

    python3 scripts/predict_from_composition.py --composition Ni46Ti28Co2Pd2Hf22
    python3 scripts/predict_from_composition.py --at Ni=46 Ti=28 Co=2 Pd=2 Hf=22

What this is, and is not
------------------------
Every model here is TRAINED AT CALL TIME from data published in this
repository. No pre-trained weights are distributed, and none of the numbers
below come from a stored model file:

  * lambda_2 and eps_tr use the vendored Transformation-Strain-Model-NiTi
    helper, whose Lambda2Model predicts lambda_2 from composition and whose
    LDT calculator converts that into a theoretical strain per loading
    direction. Same code path as scripts/compare_lambda2_ldt_models.py.

  * Delta H uses a CatBoost model fitted on THIS CAMPAIGN's 72 transforming
    alloys with a measured cycle-2 enthalpy (data/supplementary_data.xlsx),
    i.e. the `cb_comp` variant of scripts/train_dh_on_campaign.py.

    It is NOT the Delta H model used during the campaign. That one was trained
    on 833 literature entries which are not public, so it cannot be
    reproduced here. Grouped-CV accuracy of the model used here is reported
    with every prediction so the number is not mistaken for a precise value.

Transformation temperatures are opt-in, behind --with-temperatures, for two
reasons. They need a processing schedule as well as a composition, so the
model cannot answer from composition alone without assuming one; the default
is this campaign's 950 degC / 24 h homogenization, which is the only schedule
its multi-principal-element training data contains. And fitting that model
takes a few minutes, which is too slow to impose on every call.

The model is the vendored CatBoost-SMAs predictor refitted with this
campaign's own alloys added, as the campaign itself did after each iteration
(Section 2.4.1). That matters: the published literature data is entirely
ternary and quaternary, and 13 of this campaign's 14 alloy families never
appear in it, so without the campaign alloys the model is extrapolating onto
alloy families its `family` feature has never seen. See
scripts/train_tt_augmented.py for the measured accuracy of both variants.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import logging
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

ELEMENTS = ["Ni", "Ti", "Cu", "Co", "Pd", "Hf", "Zr"]
TSM_DIR = REPO / "vendored" / "Transformation-Strain-Model-NiTi"
DATA = REPO / "data" / "supplementary_data.xlsx"
STRAIN_THRESHOLD_PCT = 2.5  # Section 2.5 screening threshold


# ----------------------------------------------------------------- parsing
def parse_formula(text: str) -> dict[str, float]:
    """'Ni46Ti28Co2Pd2Hf22' -> {'Ni': 46.0, ...}."""
    pairs = re.findall(r"([A-Z][a-z]?)\s*([0-9]*\.?[0-9]+)", text)
    if not pairs:
        raise ValueError(f"could not parse a composition from {text!r}")
    comp: dict[str, float] = {}
    for el, val in pairs:
        comp[el] = comp.get(el, 0.0) + float(val)
    return comp


def parse_pairs(items: list[str]) -> dict[str, float]:
    """['Ni=46', 'Ti=28'] -> {'Ni': 46.0, ...}."""
    comp: dict[str, float] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"expected Element=at%, got {item!r}")
        el, val = item.split("=", 1)
        comp[el.strip()] = comp.get(el.strip(), 0.0) + float(val)
    return comp


def validate(comp: dict[str, float]) -> pd.DataFrame:
    unknown = sorted(set(comp) - set(ELEMENTS))
    if unknown:
        raise SystemExit(
            f"error: {', '.join(unknown)} outside the NiTi(Co,Cu,Pd,Hf,Zr) design space.\n"
            f"       supported elements: {', '.join(ELEMENTS)}"
        )
    total = sum(comp.values())
    if not 99.0 <= total <= 101.0:
        raise SystemExit(f"error: composition sums to {total:.2f} at.%, expected ~100")
    row = {el: float(comp.get(el, 0.0)) for el in ELEMENTS}
    return pd.DataFrame([row])


# ------------------------------------------------------------- predictions
def _helper():
    from compute_lambda2_eps_tr import _import_helper

    return _import_helper(TSM_DIR)


def predict_lambda2(comp_df: pd.DataFrame, helper) -> float:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        logging.getLogger().setLevel(logging.CRITICAL)
        features = helper.FeatureGenerator(comp_df[ELEMENTS])
        features.generate_composition_formula()
        out = helper.Lambda2Model(features.generate_features()).predict_transformation_and_lambda2()
    return float(out["Predicted_Lambda2"].iloc[0])


def predict_strain(lambda2: float, seed: int = 0) -> pd.DataFrame:
    """Theoretical strain per direction and loading mode, from predicted lambda_2."""
    import ast

    from compare_lambda2_ldt_models import train_strain_model

    model = train_strain_model(TSM_DIR, seed=seed)
    train = pd.read_csv(TSM_DIR / "data_for_ml.csv")
    directions = [ast.literal_eval(d) for d in train["deformation_direction"].unique()]
    rows = []
    for direction in directions:
        for mode in ("tension", "compression"):
            x = pd.DataFrame(
                {"Predicted_Lambda2": [lambda2],
                 "deformation_direction": [direction],
                 "deformation_type": [mode]}
            )
            rows.append({"direction": str(direction), "mode": mode,
                         "strain_pct": float(model.predict(x)[0])})
    return pd.DataFrame(rows)


def predict_dh(comp_df: pd.DataFrame, data_path: Path, seed: int = 0) -> tuple[float, dict]:
    """CatBoost on the seven at.% values, fitted on this campaign's measured enthalpies."""
    import catboost as cb

    from train_dh_on_campaign import ORDER, load

    df, comp_train = load(data_path)
    y = df["Average Enthalpy (J/g)"].to_numpy(float)
    x = comp_train[ORDER].to_numpy(float)

    model = cb.CatBoostRegressor(loss_function="MAE", silent=True, random_seed=seed,
                                 thread_count=4, allow_writing_files=False)
    model.fit(x, y)
    pred = float(model.predict(comp_df[ORDER].to_numpy(float))[0])

    # Honest accuracy: grouped 5-fold CV on the same data, same settings.
    from sklearn.model_selection import KFold

    errs = []
    for tr, te in KFold(n_splits=5, shuffle=True, random_state=seed).split(x):
        m = cb.CatBoostRegressor(loss_function="MAE", silent=True, random_seed=seed,
                                 thread_count=4, allow_writing_files=False)
        m.fit(x[tr], y[tr])
        errs.append(np.abs(m.predict(x[te]) - y[te]).mean())
    stats = {"n_train": len(y), "cv_mae": float(np.mean(errs)),
             "baseline_mae": float(np.abs(y - y.mean()).mean())}
    return pred, stats


# -------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--composition", help="e.g. Ni46Ti28Co2Pd2Hf22")
    src.add_argument("--at", nargs="+", metavar="EL=PCT", help="e.g. Ni=46 Ti=28 Co=2")
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-strain", action="store_true",
                    help="skip the LDT strain model (it trains a CatBoost, ~1 min)")
    ap.add_argument("--with-temperatures", action="store_true",
                    help="also predict Ms/Mf/As/Af (refits the transformation-temperature "
                         "model on literature + campaign data; takes a few minutes)")
    ap.add_argument("--final-ht-temp", type=float, default=950.0,
                    help="homogenization temperature in degC (default: the campaign's 950)")
    ap.add_argument("--final-ht-time", type=float, default=24.0,
                    help="homogenization time in hours (default: the campaign's 24)")
    args = ap.parse_args()

    try:
        comp = parse_formula(args.composition) if args.composition else parse_pairs(args.at)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    comp_df = validate(comp)
    shown = "".join(f"{el}{comp[el]:g}" for el in ELEMENTS if comp.get(el))

    print(f"composition : {shown}")
    print(f"              {', '.join(f'{el} {comp_df[el].iloc[0]:g}' for el in ELEMENTS)} at.%")
    print()

    helper = _helper()
    lam = predict_lambda2(comp_df, helper)
    print(f"lambda_2    : {lam:.4f}   (composition model; closer to 1 favours low hysteresis)")

    if not args.skip_strain:
        strain = predict_strain(lam, seed=args.seed)
        lo, hi = float(strain.strain_pct.min()), float(strain.strain_pct.max())
        tens = strain[strain["mode"] == "tension"].strain_pct
        # Deliberately NO single headline value. Two reasons:
        #
        #  * This model only knows the 12 loading directions sampled in
        #    data_for_ml.csv, and [1,1,0] is not among them, so it cannot
        #    reproduce the [110] tension figure quoted for the champion alloy
        #    in Section 3. That number comes from the lattice-parameter
        #    calculator in compute_lambda2_eps_tr.py, which needs measurements
        #    this composition-only tool does not have.
        #  * Quoting the maximum would overstate the result. The LDT model
        #    discriminates loading DIRECTION well (rho = 0.92 across cases)
        #    but has no alloy-to-alloy skill within a direction (median
        #    rho ~ -0.11; per-alloy max-strain rho ~ 0.09, not significant).
        print(f"eps_tr      : {lo:.2f}-{hi:.2f} % theoretical, across the model's "
              f"{len(strain)} direction/mode cases")
        print(f"              tension {tens.min():.2f}-{tens.max():.2f} %"
              f"{'   [range clears the 2.5 % screen]' if hi >= STRAIN_THRESHOLD_PCT else ''}")
        print("              a range, not a point estimate: this model resolves loading")
        print("              direction, not differences between alloys, and its 12 sampled")
        print("              directions exclude [110], so it is not comparable with the")
        print("              [110] value quoted in the manuscript.")
    else:
        print("eps_tr      : skipped (--skip-strain)")

    dh, st = predict_dh(comp_df, args.data, seed=args.seed)
    print(f"Delta H     : {dh:.1f} J/g")
    print(f"              campaign model, n={st['n_train']}, 5-fold CV MAE "
          f"{st['cv_mae']:.2f} J/g (mean baseline {st['baseline_mae']:.2f})")
    print()
    if args.with_temperatures:
        from train_tt_augmented import CV_MAE, DEFAULT_HT_TEMP, DEFAULT_HT_TIME
        from train_tt_augmented import predict as predict_tt

        tt, notes = predict_tt([comp], data_path=args.data, seed=args.seed,
                               ht_temp=args.final_ht_temp, ht_time=args.final_ht_time)
        row = tt.iloc[0]
        default = (args.final_ht_temp, args.final_ht_time) == (DEFAULT_HT_TEMP, DEFAULT_HT_TIME)
        print("Ms/Mf/As/Af : " + "   ".join(f"{k} {row[k]:.0f}" for k in ("Ms", "Mf", "As", "Af"))
              + " degC")
        print(f"              assuming {args.final_ht_temp:g} degC / {args.final_ht_time:g} h "
              f"homogenization" + (" -- the campaign default, applied" if default else ""))
        if default:
            print("              because none was given, not because it was measured")
        print("              out-of-sample MAE "
              + ", ".join(f"{k} {v:.0f}" for k, v in CV_MAE.items()) + " degC: this ranks")
        print("              candidates, it does not predict pointwise. Measured Ms across")
        print("              the campaign spans -73 to 399 degC.")
        for note in notes:
            print(f"              note: {note}")
    else:
        print("Ms/Mf/As/Af : not computed. Pass --with-temperatures to fit the")
        print("              transformation-temperature model (a few minutes). It needs a")
        print("              homogenization schedule as well as a composition, and defaults")
        print("              to the campaign's 950 degC / 24 h.")
    print()
    print("All models are trained at call time from data in this repository; no")
    print("pre-trained weights are distributed. The Delta H model here is fitted on")
    print("this campaign's measurements, not the literature model used during the")
    print("campaign, whose training data are not public.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
