#!/usr/bin/env python3
"""
Compare the lambda_2 phase-compatibility model and the LDT transformation-strain
model with values computed from measured lattice parameters, as reported in
Section 3 and Appendix A.7 of

    Zadeh et al., "Bayesian-Optimization-Guided Discovery of
    NiTi(Co,Cu,Pd,Hf,Zr) Multi-Principal Element High-Temperature Shape
    Memory Alloys", Acta Materialia (2026, in review).

For every alloy in the supplementary data with measured B2 (a0) and B19'
(a, b, c, beta) lattice parameters:

  * measured lambda_2:  middle eigenvalue of the lattice deformation matrix,
                        computed from the measured lattice parameters;
  * predicted lambda_2: the composition-based lambda_2 model;
  * theoretical transformation strain (Lattice Deformation Theory) in the 12
    loading directions of the strain model's training set, in tension and
    compression, computed from the measured lattice parameters and predicted
    by the CatBoost strain model applied to the predicted lambda_2. The
    CatBoost model is trained as in the vendored notebook, with a fixed seed.

It also reports the rank correlation between measured lambda_2 and the
second-cycle, stress-free DSC hysteresis DeltaT = A_f - M_s.

Both models are used from vendored/Transformation-Strain-Model-NiTi, whose
lambda_2 code is the same as that of Phase-Compatibility-Model-NiTi. The strain
part takes a few minutes because the deformation matrices are solved
symbolically; use --skip-strain for the lambda_2 results only.

Usage:  python compare_lambda2_ldt_models.py [--data PATH] [--skip-strain] [--out DIR]
"""
import argparse
import ast
import contextlib
import io
import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from compute_lambda2_eps_tr import _import_helper

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
TSM_DIR = REPO / "vendored" / "Transformation-Strain-Model-NiTi"
ELEMENTS = ["Ni", "Ti", "Cu", "Co", "Pd", "Hf", "Zr"]
LATTICE = ["a0", "a", "b", "c", "beta"]
STRAIN_THRESHOLD_PCT = 2.5  # theoretical-strain screening threshold (Section 2.5)


def load_lattice_alloys(path: Path) -> pd.DataFrame:
    """One row per alloy with measured lattice parameters and DSC hysteresis."""
    df = pd.read_excel(path, sheet_name="All Compiled Data", header=39)
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed")]
    # The lattice-parameter columns are labelled (nm) but hold values in Angstrom.
    df = df.rename(columns={f"{e} (at.%)": e for e in ELEMENTS}
                   | {"a0 (nm)": "a0", "a (nm)": "a", "b (nm)": "b", "c (nm)": "c", "β (°)": "beta"})
    df["comp_key"] = df[ELEMENTS].fillna(0).round(2).astype(str).agg("|".join, axis=1)
    keys = ["Iteration", "comp_key"]
    cycle2 = df[df["DSC Cycle Number"] == 2].set_index(keys)
    lattice = (
        df.dropna(subset=LATTICE)
        .sort_values("DSC Cycle Number", ascending=False)  # prefer the cycle-2 row
        .groupby(keys)
        .first()
    )
    out = lattice[ELEMENTS + LATTICE].copy()
    out[ELEMENTS] = out[ELEMENTS].fillna(0).astype(float)
    out["DT_dsc"] = (cycle2["Af (°C)"] - cycle2["Ms (°C)"]).reindex(out.index)
    return out.reset_index()


def add_lambda2(alloys: pd.DataFrame, helper) -> pd.DataFrame:
    alloys = alloys.copy()
    alloys["lambda2_meas"] = [
        helper.LambdaCalculator.calculate_lambdas(r.a0, r.a, r.b, r.c, r.beta)[1]
        for r in alloys.itertuples()
    ]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        logging.getLogger().setLevel(logging.CRITICAL)
        features = helper.FeatureGenerator(alloys[ELEMENTS])
        features.generate_composition_formula()
        predicted = helper.Lambda2Model(features.generate_features()).predict_transformation_and_lambda2()
    alloys["lambda2_pred"] = predicted["Predicted_Lambda2"].to_numpy(float)
    return alloys


def strain_directions(tsm_dir: Path) -> list:
    train = pd.read_csv(tsm_dir / "data_for_ml.csv")
    return [ast.literal_eval(d) for d in train["deformation_direction"].unique()]


def measured_strains(alloys: pd.DataFrame, helper, directions: list) -> pd.DataFrame:
    """LDT tensile and compressive strain (%) from the measured lattice parameters."""
    rows = []
    for r in alloys.itertuples():
        calc = helper.TransformationStrainCalculator()
        calc.set_lattice_constants_and_beta(r.a0, r.a, r.b, r.c, r.beta)
        # Solve the deformation matrices once per alloy, then evaluate every direction
        # (same steps as TransformationStrainCalculator.calc_max_strain_and_info).
        matrices = [calc.symbolic_matrix_to_numpy(calc.solve_equations(*lc)) for lc in calc.lattice_constants_sets]
        for direction in directions:
            calc.set_custom_directions(direction)
            eps = [calc.calculate_transformation_strain(calc.deformation_directions, m) for m in matrices]
            for mode, value in (("tension", calc.calculate_tensile_transformation_strain(eps)),
                                ("compression", calc.calculate_compressive_transformation_strain(eps))):
                rows.append({"alloy": r.Index, "direction": str(direction), "deformation_type": mode,
                             "strain_meas": float(value)})
    return pd.DataFrame(rows)


def train_strain_model(tsm_dir: Path, seed: int = 0):
    from catboost import CatBoostRegressor

    train = pd.read_csv(tsm_dir / "data_for_ml.csv")
    train["deformation_direction"] = train["deformation_direction"].apply(ast.literal_eval)
    model = CatBoostRegressor(silent=True, cat_features=["deformation_type"],
                              embedding_features=["deformation_direction"],
                              random_seed=seed, allow_writing_files=False)
    model.fit(train[["Predicted_Lambda2", "deformation_direction", "deformation_type"]],
              train["LDT_transformation_strain"])
    return model


def correlation(y, p) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    ok = ~(np.isnan(y) | np.isnan(p))
    res = spearmanr(y[ok], p[ok])
    return {"n": int(ok.sum()), "rho": float(res.statistic), "p": float(res.pvalue),
            "mae": float(np.abs(y[ok] - p[ok]).mean()), "bias": float((p[ok] - y[ok]).mean())}


def run(data_path: Path, tsm_dir: Path = TSM_DIR, strain: bool = True) -> dict:
    helper = _import_helper(tsm_dir)
    alloys = add_lambda2(load_lattice_alloys(data_path), helper)
    results = {
        "alloys": alloys,
        "n_alloys": len(alloys),
        "lambda2": correlation(alloys.lambda2_meas, alloys.lambda2_pred),
        "lambda2_by_iteration": {int(it): correlation(g.lambda2_meas, g.lambda2_pred)
                                 for it, g in alloys.groupby("Iteration")},
        "lambda2_vs_dT": correlation(alloys.lambda2_meas, alloys.DT_dsc),
    }
    if strain:
        rows = measured_strains(alloys, helper, strain_directions(tsm_dir))
        rows = rows.merge(alloys[["Iteration", "lambda2_pred"]], left_on="alloy", right_index=True)
        query = pd.DataFrame({
            "Predicted_Lambda2": rows["lambda2_pred"],
            "deformation_direction": rows["direction"].apply(ast.literal_eval),
            "deformation_type": rows["deformation_type"],
        })
        rows["strain_pred"] = train_strain_model(tsm_dir).predict(query)
        lowest = rows.groupby("alloy")[["strain_meas", "strain_pred"]].min()
        results.update({
            "strain_rows": rows,
            "strain": correlation(rows.strain_meas, rows.strain_pred),
            "strain_min_meas_pct": float(lowest.strain_meas.min()),
            "strain_min_pred_pct": float(lowest.strain_pred.min()),
            "n_above_threshold_meas": int((lowest.strain_meas >= STRAIN_THRESHOLD_PCT).sum()),
            "n_above_threshold_pred": int((lowest.strain_pred >= STRAIN_THRESHOLD_PCT).sum()),
        })
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=REPO / "data" / "supplementary_data.xlsx")
    ap.add_argument("--tsm-dir", type=Path, default=TSM_DIR)
    ap.add_argument("--skip-strain", action="store_true", help="lambda_2 results only (fast)")
    ap.add_argument("--out", type=Path, help="directory for per-alloy CSV outputs")
    args = ap.parse_args()

    r = run(args.data, args.tsm_dir, strain=not args.skip_strain)
    a = r["alloys"]
    print(f"Alloys with measured B2 and B19' lattice parameters: {r['n_alloys']} "
          f"(Iterations 1/2/3: {'/'.join(str(n) for n in a.Iteration.value_counts().sort_index())})")
    print(f"Measured lambda_2 {a.lambda2_meas.min():.4f}-{a.lambda2_meas.max():.4f}; "
          f"predicted {a.lambda2_pred.min():.3f}-{a.lambda2_pred.max():.3f}")

    print("\nlambda_2: composition-based model vs measured lattice parameters")
    print(f"  {'':<12}{'n':>4}{'rho':>8}{'p':>11}{'MAE':>9}{'bias':>9}")
    for label, m in [*((f"Iteration {k}", v) for k, v in r["lambda2_by_iteration"].items()), ("All", r["lambda2"])]:
        print(f"  {label:<12}{m['n']:>4}{m['rho']:>8.3f}{m['p']:>11.2e}{m['mae']:>9.4f}{m['bias']:>9.4f}")

    m = r["lambda2_vs_dT"]
    print(f"\nMeasured lambda_2 vs DSC hysteresis (A_f - M_s): Spearman rho {m['rho']:.3f} "
          f"(p = {m['p']:.2e}, n = {m['n']})")

    if "strain" in r:
        m = r["strain"]
        print("\nLDT theoretical strain: CatBoost model (predicted lambda_2) vs measured lattice parameters")
        print(f"  {m['n']} cases (12 directions x tension/compression x {r['n_alloys']} alloys): "
              f"Spearman rho {m['rho']:.3f}, MAE {m['mae']:.2f}%")
        print(f"  Lowest strain over all directions and modes: measured {r['strain_min_meas_pct']:.2f}%, "
              f"model {r['strain_min_pred_pct']:.2f}%")
        print(f"  Alloys at or above the {STRAIN_THRESHOLD_PCT}% screening threshold in every case: "
              f"measured {r['n_above_threshold_meas']}/{r['n_alloys']}, model {r['n_above_threshold_pred']}/{r['n_alloys']}")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        a.to_csv(args.out / "lambda2_by_alloy.csv", index=False)
        if "strain_rows" in r:
            r["strain_rows"].to_csv(args.out / "ldt_strain_by_alloy_direction.csv", index=False)
        print(f"\nCSV outputs written to {args.out}")


if __name__ == "__main__":
    main()
