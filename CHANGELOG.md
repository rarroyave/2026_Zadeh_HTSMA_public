# Changelog

All notable changes to this repository will be documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] --- 2026-09-01

Initial release accompanying manuscript submission.

### Added

- `data/supplementary_data.xlsx` --- 87-alloy experimental dataset (DSC +
  UCFTC + ML predictions + XRD lattice parameters) forming the manuscript's
  Supplementary Information.
- `data/README.md` --- data dictionary scoped to the SI workbook.
- `scripts/compute_spearman_mae.py` --- reproduces Table 5 (Spearman rho and
  MAE for M_s, A_f, DeltaT, DeltaH, per iteration and aggregated).
- `scripts/compute_four_pass_rates.py` --- reproduces the per-iteration
  four-functional-target hit rates (Appendix A).
- `scripts/compute_lambda2_eps_tr.py` --- reproduces the champion-alloy and
  reference-alloy Ball--James geometric compatibility (lambda_1, lambda_2,
  lambda_3) and theoretical single-crystal transformation strain in five
  crystallographic directions.
- `notebooks/reproduce_manuscript_figures.ipynb` --- executable Jupyter
  walk-through of all three scripts with inline visualizations.
- `tests/` --- 4 pytest regression checks verifying the manuscript's key
  numbers (champion lambda_2 = 0.945, champion eps_tr [110] tension = 12.3%,
  87 aggregated alloy rows, Table 5 rho_Ms progression).
- Zadeh et al.'s Phase-Compatibility-Model-NiTi and
  Transformation-Strain-Model-NiTi vendored verbatim under `vendored/` (from
  upstream commits `a1b4fd8` and `2c0ef08` respectively), with per-directory
  `NOTICE.md` recording provenance. Vendored rather than referenced as
  submodules so the archive is self-contained.
- GitHub Actions CI (`.github/workflows/ci.yml`) --- matrix Python 3.10 / 3.11
  / 3.12 runs the pytest suite plus all four reproduction paths (three scripts
  + notebook execution) on every push.
