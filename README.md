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
├── data/
│   ├── supplementary_data.xlsx    87 alloys x DSC + UCFTC + ML preds + XRD
│   └── README.md                  data dictionary
├── scripts/
│   ├── compute_spearman_mae.py         Table 5 (Spearman rho + MAE)
│   ├── compute_four_pass_rates.py      Appendix A four-target hit rates
│   └── compute_lambda2_eps_tr.py       champion-alloy lambda_2 and eps_tr
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
key result --- Iteration 1 rho_Ms = 0.25 rising to Iteration 3 rho_Ms = 0.73 ---
reflects the Bayesian optimization loop adaptively retraining the surrogate
with each round of new MPE observations.

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
(Latin-hypercube batch) that seeded the campaign and did not require the BO
loop; see the vendored
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

Three regressions verify the champion-alloy lambda_2, the shape of the SI
table, and the Table 5 rho_Ms progression against the values reported in the
manuscript.

## Supplementary analysis: ΔH models trained on the campaign data

Not reported in the manuscript. The ΔH predictions used during the campaign came
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
indicative only. The script needs `catboost` and HEACalculator 1.3.0.

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
