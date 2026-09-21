# NiTi(Co,Cu,Pd,Hf,Zr) MPE HTSMA --- supplementary data + reproduction scripts

[![CI](https://github.com/rarroyave/2026_Zadeh_HTSMA_public/actions/workflows/ci.yml/badge.svg)](https://github.com/rarroyave/2026_Zadeh_HTSMA_public/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Data: CC BY 4.0](https://img.shields.io/badge/Data-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22256930.svg)](https://doi.org/10.5281/zenodo.22256930)

Public companion to:

> Zadeh, S. H.; Broucek, J.; Cakirhan, C.; Li, M.; Khatamsaz, D.; Qian, X.;
> Karaman, I.; Arroyave, R. **Bayesian-Optimization-Guided Discovery of
> NiTi(Co,Cu,Pd,Hf,Zr) Multi-Principal Element High-Temperature Shape Memory
> Alloys.** *Acta Materialia* (2026, in review).

This repository contains the 87-alloy experimental dataset presented in the
manuscript's Supplementary Information and short Python scripts that reproduce
the specific numerical results reported in Section 3 and Appendix A.

## Contents

```
2026_Zadeh_HTSMA_public/
├── README.md               (this file)
├── LICENSE                 MIT (code) / CC BY 4.0 (data --- see data/README.md)
├── CITATION.cff            citation metadata
├── requirements.txt        Python dependencies for the analysis scripts + notebook
├── requirements-bo.txt     extra deps for the Bayesian-optimization campaign code
├── paper/
│   └── 2026-zadeh-htsma-R1.pdf    revised manuscript (clean, two-column)
├── data/
│   ├── supplementary_data.xlsx    87 alloys x DSC + UCFTC + ML preds + XRD
│   └── README.md                  data dictionary
├── scripts/
│   ├── compute_spearman_mae.py         Table 5 (Spearman rho + MAE)
│   ├── compute_four_pass_rates.py      Appendix A four-target hit rates
│   ├── compute_pareto_membership.py    Section 3 / Appendix A.6 Pareto-front membership
│   ├── compute_lambda2_eps_tr.py       champion-alloy lambda_2 and eps_tr
│   ├── compare_lambda2_ldt_models.py   lambda_2 and LDT strain models vs measured lattice parameters
│   ├── train_dh_on_campaign.py         supplementary ΔH analysis (Appendix B)
│   ├── train_tt_augmented.py           transformation-temperature model + campaign data
│   └── predict_from_composition.py     predict properties for one composition
├── tests/                              pytest regressions vs. manuscript values
├── notebooks/
│   └── reproduce_manuscript_figures.ipynb
├── .github/workflows/ci.yml            GitHub Actions CI (Py 3.10, 3.11, 3.12)
└── vendored/                           verbatim snapshots of related repos
    ├── CatBoost-SMAs/                      transformation-temperature model (Comput. Mater. Sci. 226, 2023)
    ├── Phase-Compatibility-Model-NiTi/     lambda_1/2/3 calculator (Mater. Des. 244, 2024)
    ├── Transformation-Strain-Model-NiTi/   eps_tr calculator (in preparation)
    └── NiTi-alloy-discovery/               Bayesian-optimization campaign engine and ML-model code
```

The `vendored/` directories are snapshots of related MIT-licensed repositories
that this bundle depends on. Each subdirectory carries its own `LICENSE` and
a `NOTICE.md` recording the upstream repository URL, the exact commit SHA
it was taken from, and any local patches. Vendoring these here (rather than referencing them as git
submodules) makes the archive self-contained --- a download from Zenodo will
still work if the upstream GitHub repos ever move or disappear.

## The paper

`paper/2026-zadeh-htsma-R1.pdf` is the revised manuscript (R1) as submitted to
Acta Materialia, in the clean two-column format without revision markup. The
numbers reproduced by the scripts below refer to this version.

## Install

```bash
git clone <this repo>
cd 2026_Zadeh_HTSMA_public
pip install -r requirements.txt
pip install --no-deps "HEACalculator @ git+https://github.com/dogusariturk/HEACalculator@v.1.3.0"
```

To additionally run the Bayesian-optimization campaign under
`vendored/NiTi-alloy-discovery/`:

```bash
pip install -r requirements-bo.txt
```

## Reproduce the manuscript numbers

**Section 3 --- implicit MPE hold-out (Table 5):**

```bash
python scripts/compute_spearman_mae.py
```

Reports per-iteration Spearman rho and MAE for M_s, A_f, DeltaT, DeltaH. The
key result --- Iteration 1 rho_Ms = 0.27 rising to Iteration 3 rho_Ms = 0.73 ---
reflects the Bayesian optimization loop adaptively retraining the surrogate
with each round of new MPE observations.

**Section 3 and Appendix A.7 --- lambda_2 and LDT strain models vs measured lattice parameters:**

```bash
python scripts/compare_lambda2_ldt_models.py            # add --skip-strain for lambda_2 only, --out DIR for CSVs
```

For the 70 alloys with measured B2 and B19' lattice parameters (20, 23, and 27
in Iterations 1--3), compares the composition-based lambda_2 model and the LDT
transformation-strain model with values computed from those lattice parameters.

| Comparison | Result |
| --- | --- |
| lambda_2 model vs measured lambda_2 (70 alloys) | Spearman rho 0.49 (p = 1.4e-5), MAE 0.012 |
| LDT strain model vs measured-lattice strain (12 directions x tension/compression) | Spearman rho 0.92, MAE 1.08% |
| Alloys at or above the 2.5% theoretical-strain threshold in every direction and mode | 70/70 (model and measured) |
| Measured lambda_2 vs DSC hysteresis A_f - M_s | Spearman rho -0.44 (p = 1.4e-4) |

The original accuracy of the lambda_2 model is MAE 0.01 (Mater. Des. 244, 2024).
The strain part takes a few minutes; the script needs `catboost`.

**Section 3 --- champion-alloy crystallographic compatibility and strain:**

```bash
python scripts/compute_lambda2_eps_tr.py
```

Reports lambda_1/lambda_2/lambda_3 and single-crystal eps_tr in five
crystallographic directions for Ni46Ti28Co2Pd2Hf22 (champion) and
Ni45Ti25Co5Hf11Zr14 (lowest-DeltaT reference).

**Section 3 --- per-iteration four-target hit rates:**

```bash
python scripts/compute_four_pass_rates.py
```

Reports the fraction of alloys in each iteration that jointly satisfy:
M_s in [200, 400] deg C, second-cycle stress-free DSC
DeltaT = A_f - M_s <= 50 deg C, DeltaH >= 20 J/g, and eps_tr >= 2.5%.
Iteration 1's 21% joint pass rate is the calibration point for Appendix A.

**Section 3 and Appendix A.6 --- Pareto-front membership by iteration:**

```bash
python scripts/compute_pareto_membership.py
```

Objective space (-DeltaT, DeltaH, eps_tr) over the 31 strain-tested alloys,
with DeltaT the midpoint hysteresis A50 - M50 from the second DSC cycle, DeltaH
the second-cycle average enthalpy, and eps_tr the largest measured
transformation strain. Reports the cumulative front after Iteration 2
(8 alloys: 3 from Iteration 1, 5 from Iteration 2), the final front (10 alloys,
2/3/5 by iteration; rates 0.20/0.27/0.50), the 3 earlier front alloys dominated
by Iteration 3, and Pr(Z >= 5 | Binomial(10, 0.20)) = 0.033.

## Re-running the Bayesian-optimization campaign

The BO loop that drove the alloy selection across three iterations is under
`vendored/NiTi-alloy-discovery/`. From either iteration directory:

```bash
cd vendored/NiTi-alloy-discovery/Iter2   # or Iter3
python main.py
```

The loop reads the tested-alloy outcomes (`o1_GT_y.csv`, `o2_GT_y.csv`,
`o3_GT_y.csv` for the three objectives --- minimize hysteresis, maximize
enthalpy, maximize transformation strain) and the feasibility labels
(`feasibles.csv` / `infeasibles.csv`) that come out of the probability
sub-pipeline in `Probability_calculations/`, fits a Gaussian-process
surrogate, and proposes the next batch. Iteration 1 was the initial design
(K-medoid seeding of the 17,207 CALPHAD-filtered candidates) that seeded the
campaign and did not require the BO loop; see the vendored
directory's `NOTICE.md` for the full contents map and for the list of large
intermediate CSVs that were stripped and are regenerable at runtime.

## Rendered walk-through

For a browseable version of the three scripts with inline visualizations
(rho_Ms progression bar chart, per-iteration four-target hit rates,
champion-alloy lambda_2 and eps_tr direction-by-direction), open:

```
notebooks/reproduce_manuscript_figures.ipynb
```

The notebook is pre-executed so the figures render on GitHub / Zenodo
without needing to run Jupyter locally.

## Reproducibility tests

```bash
pip install pytest
pytest tests/ -v
```

The tests check the numbers reported in the manuscript: the champion-alloy
lambda_2 and eps_tr, the shape of the SI table, Table 5, the four-target hit
rates, the Pareto-front membership, the Table B1 hyperparameters in the vendored model code, the
HEACalculator compatibility layer, the supplementary ΔH analysis, and the
comparison of the lambda_2 and LDT strain models with measured lattice
parameters.

## Supplementary analysis: ΔH models trained on the campaign data

Summarized in Appendix B of the revised manuscript. The ΔH predictions used during the campaign came
from a CatBoost model trained on a larger literature database that is not part
of this repository. `scripts/train_dh_on_campaign.py` asks how well ΔH can be
predicted from the campaign's own measurements: the second-cycle DSC
enthalpies of the 72 transforming alloys with a measured ΔH (23, 23, and 26 in
Iterations 1--3).

```bash
python scripts/train_dh_on_campaign.py            # add --out DIR for CSV outputs
```

Repeated 5-fold cross-validation (10 repeats, folds grouped by composition;
mean ± sd over repeats). The campaign model's own predictions on the same 72
alloys give MAE 7.27 J/g (the Table 5 value), R² −1.03, and ρ 0.50.

| Model | MAE (J/g) | RMSE (J/g) | R² | Spearman ρ |
| --- | ---: | ---: | ---: | ---: |
| Predict the mean | 4.72 ± 0.06 | 6.30 | -0.03 | -0.18 |
| Ridge, at.% | 3.62 ± 0.17 | 5.20 | 0.30 | 0.69 |
| CatBoost, at.% | 3.18 ± 0.13 | 4.17 | 0.55 | 0.70 |
| CatBoost, six notebook descriptors | 3.77 ± 0.22 | 5.19 | 0.30 | 0.66 |

Forward in time (train on earlier iterations, predict the next one):

| Model | Iter 1 → 2: MAE / ρ | Iter 1+2 → 3: MAE / ρ |
| --- | ---: | ---: |
| Predict the mean | 3.87 / – | 5.78 / – |
| Ridge, at.% | 2.94 / 0.49 | 3.03 / 0.55 |
| CatBoost, at.% | 3.66 / 0.58 | 3.28 / 0.58 |
| CatBoost, six notebook descriptors | 3.90 / 0.53 | 4.61 / 0.21 |
| Campaign model (predictions used in the BO loop) | 6.04 / 0.71 | 4.54 / 0.66 |

Models fitted to the campaign alloys roughly halve the absolute error of the
literature-trained model. For ranking the next iteration's alloys, however, the
campaign model is as good or better, consistent with the manuscript's use of the
surrogates as rank-ordering priors. The six descriptors selected for the
literature data do not transfer better than plain composition. The test sets are
small (23--26 alloys) and the ΔH range is narrow, so these numbers are
indicative only. The script needs `catboost`, `scikit-learn`, and HEACalculator 1.3.0.

## Predicting properties for a composition

```bash
python scripts/predict_from_composition.py --composition Ni46Ti28Co2Pd2Hf22
python scripts/predict_from_composition.py --at Ni=46 Ti=28 Co=2 Pd=2 Hf=22
```

Reports λ₂, the theoretical transformation strain, and ΔH for one composition in
the NiTi(Co,Cu,Pd,Hf,Zr) design space. Every model is trained at call time from
data in this repository; no pre-trained weights are distributed.

ε_tr is reported as a range rather than a single value. The LDT model resolves
loading *direction* well (ρ = 0.92 across direction/mode cases) but has no
alloy-to-alloy skill within a direction, and its twelve sampled directions
exclude [110], so it is not comparable with the [110] figure quoted in Section 3.

### Transformation temperatures

Add `--with-temperatures` to also predict M_s, M_f, A_s and A_f. This is opt-in
because it refits the transformation-temperature model, which takes about seven
minutes, and because it needs a homogenization schedule as well as a
composition. It defaults to the campaign's 950 °C / 24 h and says so:

```
Ms/Mf/As/Af : Ms 218   Mf 186   As 229   Af 244 degC
              assuming 950 degC / 24 h homogenization -- the campaign default, applied
              because none was given, not because it was measured
              out-of-sample MAE Ms 53, Mf 50, As 60, Af 62 degC: this ranks
              candidates, it does not predict pointwise.
```

Use `--final-ht-temp` and `--final-ht-time` for a different schedule; the script
then warns, because every multi-principal-element alloy in the training data was
homogenized at 950 °C / 24 h.

The model is the vendored CatBoost-SMAs predictor refitted with this campaign's
alloys added, which is what the campaign itself did after each iteration
(Section 2.4.1). That matters more than it sounds: the published literature data
is entirely ternary and quaternary, and **thirteen of this campaign's fourteen
alloy families never appear in it**, so the `family` categorical feature has
never seen them. `scripts/train_tt_augmented.py` measures what that is worth,
grouped 5-fold over the campaign alloys:

| Target | Literature only | Augmented |
| --- | ---: | ---: |
| M_s | 69.2 °C | **48.5 °C** |
| M_f | 65.9 °C | **45.2 °C** |
| A_s | 96.1 °C | **59.5 °C** |
| A_f | 96.0 °C | **62.4 °C** |

Roughly 49 °C of error on M_s is large next to the −73 to +399 °C span of the
measured data. These models rank candidates; they are not pointwise predictors,
which is how the manuscript uses them.

```bash
python scripts/train_tt_augmented.py     # recompute the tables above (~40 min)
```

## Licensing

- **Code** (this repo, minus `vendored/`) --- MIT License (`LICENSE`).
- **HEACalculator** (Doguhan Sariturk, GPL-3.0) is a separately installed
  dependency and is not redistributed here; `heacalc_compat.py` adapts its
  published 1.3.0 interface for the vendored helper modules.
- **Data** (`data/supplementary_data.xlsx`) --- CC BY 4.0. Please cite the paper.
- **Vendored submodules** --- separately MIT-licensed by S. Hossein Zadeh.
  See each submodule's own `LICENSE` file.

## Related resources

- [CatBoost-SMAs](https://github.com/sinazadeh/CatBoost-SMAs) --- CatBoost
  surrogate model for SMA transformation temperatures
  (Zadeh et al., Comput. Mater. Sci. 226 (2023) 112225).
- [Phase-Compatibility-Model-NiTi](https://github.com/sinazadeh/Phase-Compatibility-Model-NiTi)
  (Zadeh et al., Mater. Des. 244 (2024) 113096). Vendored as a submodule.
- [Transformation-Strain-Model-NiTi](https://github.com/sinazadeh/Transformation-Strain-Model-NiTi)
  (Zadeh et al., in preparation). Vendored as a submodule.

## Credits

This paper and its reproducibility bundle are the result of a multi-year
collaborative effort. Contributions by author (in paper order):

- **S. Hossein Zadeh** --- first author; developed the three surrogate
  models (CatBoost transformation temperatures, `lambda_2` phase
  compatibility, theoretical `eps_tr`) that form the property-prediction
  backbone; led ML/BO integration. Framed the unified multi-source
  optimization workflow in his 2026 Texas A&M Ph.D. dissertation, "Multi-
  Source Optimization Framework for Materials Discovery in Multi-Component
  NiTi Shape Memory Alloys."
- **John Broucek** --- led the experimental synthesis and characterization
  of the 87 MPE HTSMAs (vacuum arc melting, DSC, UCFTC per ASTM E3097,
  XRD, SEM/EDX).
- **Cem Cakirhan** --- experimental synthesis and characterization support.
- **Mingqian Li** --- computational support (feature engineering, ML
  model integration).
- **Danial Khatamsaz** --- primary code author of the
  Bayesian-optimization campaign engine under
  `vendored/NiTi-alloy-discovery/`: Gaussian-process surrogates,
  multi-objective EHVI acquisition, reification-based information fusion,
  feasibility-probability sub-pipeline.
- **Xiaoning Qian** --- co-supervisor; Bayesian-optimization and
  Gaussian-process methodology.
- **Ibrahim Karaman** --- corresponding author (materials-science side);
  experimental campaign design and mechanical-behaviour interpretation.
- **Raymundo Arroyave** --- corresponding author (computational side);
  overall project direction, ICME/BO framework, and this reproducibility
  bundle.

### Software attribution

The property-prediction models used throughout this repository are
Sina Zadeh's publicly-released work:

- [github.com/sinazadeh/CatBoost-SMAs](https://github.com/sinazadeh/CatBoost-SMAs)
  --- transformation-temperature surrogate
  (Zadeh et al., *Comput. Mater. Sci.* 226 (2023) 112225).
- [github.com/sinazadeh/Phase-Compatibility-Model-NiTi](https://github.com/sinazadeh/Phase-Compatibility-Model-NiTi)
  --- `lambda_1`, `lambda_2`, `lambda_3` calculator
  (Zadeh et al., *Mater. Des.* 244 (2024) 113096).
- [github.com/sinazadeh/Transformation-Strain-Model-NiTi](https://github.com/sinazadeh/Transformation-Strain-Model-NiTi)
  --- theoretical single-crystal `eps_tr` calculator
  (Zadeh et al., in preparation).

The BO campaign engine at `vendored/NiTi-alloy-discovery/` was primarily
authored by Danial Khatamsaz. See each vendored directory's `NOTICE.md`
for the pinned upstream commit and full attribution.

## Citing

If you use this dataset or these scripts, please cite the paper (above),
the vendored calculator whose numbers you reproduce (Sina Zadeh's
publications), and, if you use the BO loop, the paper's methods section
(Khatamsaz + Zadeh + team).

## Contact

Raymundo Arroyave --- `rarroyave@tamu.edu`
