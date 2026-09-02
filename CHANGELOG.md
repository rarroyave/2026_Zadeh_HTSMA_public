# Changelog

All notable changes to this repository will be documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] --- 2026-09-02

### Added

- `vendored/NiTi-alloy-discovery/` --- vendored snapshot of the
  Bayesian-optimization campaign engine (upstream commit `28dbc74`), with the
  Iter2 and Iter3 loop code, Gaussian-process surrogate, multi-objective
  acquisition (EHVI), reification-based information fusion, feasibility
  probability sub-pipeline, and per-iteration campaign state. Primary code
  contributor: Danial Khatamsaz. MIT-licensed under authority of the paper's
  author team.
- `requirements-bo.txt` --- optional dependencies (`george`, `pyDOE`,
  `scikit-learn-extra`) for running the BO loop.
- README section "Re-running the Bayesian-optimization campaign" pointing at
  `Iter{2,3}/main.py`.

### Changes vs. the upstream BO snapshot

- `Iter{2,3}/all_space.csv` (top-level, ~128 MB each) --- stripped. Runtime-
  derivable from the shipped `feasibles.csv` + `infeasibles.csv` via
  `np.concatenate`, so not needed to run the top-level BO loop.
- `Iter{2,3}/Probability_calculations/itr{2,3}/all_space.csv` (~128 MB
  each) --- not shipped; regenerable as a byte-exact 3,812,408-row set via
  `vendored/NiTi-alloy-discovery/generate_design_space.py` in ~15 s. The
  generator was derived from Sina's dissertation Section 4.2.3 and
  cross-validated against the original CSV. See the vendored `NOTICE.md`
  for the full spec and reproduction instructions.
- `Iter3/Summary.pptx` --- stripped. Personal working slide deck.

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
