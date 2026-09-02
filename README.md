# NiTi(Co,Cu,Pd,Hf,Zr) MPE HTSMA --- supplementary data + reproduction scripts

[![CI](https://github.com/rarroyave/2026_Zadeh_HTSMA_public/actions/workflows/ci.yml/badge.svg)](https://github.com/rarroyave/2026_Zadeh_HTSMA_public/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Data: CC BY 4.0](https://img.shields.io/badge/Data-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
<!-- Replace the pending DOI badge below once a Zenodo release is minted. -->
[![DOI](https://img.shields.io/badge/DOI-pending-lightgrey.svg)](#)

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
    ├── Phase-Compatibility-Model-NiTi/     lambda_1/2/3 calculator (Mater. Des. 244, 2024)
    ├── Transformation-Strain-Model-NiTi/   eps_tr calculator (in preparation)
    └── NiTi-alloy-discovery/               Bayesian-optimization campaign engine
```

The `vendored/` directories are snapshots of related MIT-licensed repositories
that this bundle depends on. Each subdirectory carries its own `LICENSE` and
a `NOTICE.md` recording the upstream repository URL and the exact commit SHA
it was taken from. Vendoring these here (rather than referencing them as git
submodules) makes the archive self-contained --- a download from Zenodo will
still work if the upstream GitHub repos ever move or disappear.

## Install

```bash
git clone <this repo>
cd 2026_Zadeh_HTSMA_public
pip install -r requirements.txt
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
crystallographic directions for Ni46Ti28Hf22Pd2Co2 (champion) and
Ni45Ti25Co5Hf11Zr14 (lowest-DeltaT reference).

**Section 3 --- per-iteration four-target hit rates:**

```bash
python scripts/compute_four_pass_rates.py
```

Reports the fraction of alloys in each iteration that jointly satisfy:
M_s in [200, 400] deg C, DeltaT (UCFTC) <= 50 deg C, DeltaH >= 20 J/g,
eps_tr >= 2.5%. Iteration 1's 21% joint pass rate is the calibration point
for Appendix A.

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

## Licensing

- **Code** (this repo, minus `vendored/`) --- MIT License (`LICENSE`).
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

This reproducibility bundle relies heavily on **S. Hossein Zadeh's** prior
methodological work, without which the paper this repository accompanies
would not exist. Three of the four vendored subdirectories are verbatim
snapshots of his publicly-released model repositories, and the corresponding
methods (CatBoost transformation-temperature prediction, `lambda_2` phase
compatibility, theoretical transformation strain) form the property-
prediction backbone of the Bayesian-optimization campaign:

- [github.com/sinazadeh/CatBoost-SMAs](https://github.com/sinazadeh/CatBoost-SMAs)
  --- transformation-temperature surrogate
  (Zadeh et al., *Comput. Mater. Sci.* 226 (2023) 112225).
- [github.com/sinazadeh/Phase-Compatibility-Model-NiTi](https://github.com/sinazadeh/Phase-Compatibility-Model-NiTi)
  --- `lambda_1`, `lambda_2`, `lambda_3` calculator
  (Zadeh et al., *Mater. Des.* 244 (2024) 113096).
- [github.com/sinazadeh/Transformation-Strain-Model-NiTi](https://github.com/sinazadeh/Transformation-Strain-Model-NiTi)
  --- theoretical single-crystal `eps_tr` calculator
  (Zadeh et al., in preparation).

The unified `Multi-Source Optimization Framework for Materials Discovery in
Multi-Component NiTi Shape Memory Alloys` --- Sina's 2026 Ph.D. dissertation
at Texas A&M University --- integrates these three methods into the closed-
loop discovery workflow demonstrated in this paper. If you use any part of
`vendored/Phase-Compatibility-Model-NiTi/`,
`vendored/Transformation-Strain-Model-NiTi/`, or their calculators exposed
via `scripts/compute_lambda2_eps_tr.py`, please cite the corresponding paper
above.

The Bayesian-optimization campaign engine under
`vendored/NiTi-alloy-discovery/` was primarily authored by
**Danial Khatamsaz** (Gaussian-process surrogates, multi-objective EHVI
acquisition, reification-based information fusion, feasibility-probability
sub-pipeline). See `vendored/NiTi-alloy-discovery/NOTICE.md` for the full
attribution.

## Citing

If this dataset or these scripts are useful to you, please cite the paper
(above), the vendored calculator whose numbers you reproduce (Sina's
publications), and, if you use the BO loop, the paper's methods section
(Khatamsaz + Zadeh + Arroyave).

## Contact

Raymundo Arroyave --- `rarroyave@tamu.edu`
