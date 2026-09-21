# Changelog

All notable changes to this repository will be documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.8] --- 2026-09-21

### Added

- `scripts/predict_from_composition.py`: predict properties for a single
  composition in the NiTi(Co,Cu,Pd,Hf,Zr) design space. Reports λ₂, the
  theoretical transformation strain (as a range, since the LDT model resolves
  loading direction rather than differences between alloys) and ΔH.

- `scripts/train_tt_augmented.py`: the vendored CatBoost-SMAs
  transformation-temperature model refitted with this campaign's alloys added,
  as the campaign itself did after each iteration. The published literature
  data is entirely ternary and quaternary and thirteen of this campaign's
  fourteen alloy families never appear in it, so without the campaign alloys
  the model extrapolates onto families its `family` categorical has never seen.
  Grouped 5-fold over the 81 campaign alloys, MAE falls from 69.2 to 48.5 °C
  on M_s and from 96.0 to 62.4 °C on A_f. Exposed through the wrapper's opt-in
  `--with-temperatures` flag, which defaults to the campaign's 950 °C / 24 h
  homogenization and warns when a different schedule is supplied.

  This also makes the vendored model runnable under the pandas version this
  repository pins. CBFV's `extend_features` path takes the median of every
  column, which pandas 1.5 restricted to numeric columns and pandas 2 does not,
  so `vendored/CatBoost-SMAs/main.py` cannot run here as written. Generating the
  composition features alone and reattaching the remaining columns reproduces
  the pandas 1.5 behaviour, checked against the upstream run recorded in
  `vendored/CatBoost-SMAs/NOTICE.md` (RMSE 24.8 / MAE 17.2 / R² 0.936 here
  versus 24.7 / 17.0 / 0.936 there).

- `tests/test_tt_augmented.py`: 13 tests. Twelve are structural and fast --
  record selection, alloy-family coverage, feature alignment between the
  training and query matrices, the default processing schedule, and a drift
  guard that fails if the ported hyperparameters stop matching
  `vendored/CatBoost-SMAs/main.py`. The thirteenth fits the model once and
  checks it recovers alloys it was trained on, which takes about seven
  minutes; its tolerance is deliberately loose, because its job is to catch a
  pipeline that has stopped working rather than to pin values that move with
  library versions.

### Fixed

- `data/supplementary_data.xlsx`: corrected two transcription errors, each a
  single cell, in rows that recorded a martensite finish above the martensite
  start (`M_f > M_s`, not physically possible). They were the only two such
  rows of 174, and both were verified against the raw DSC traces by the author
  who produced the measurements.

  - Ni50Ti25Hf19Zr6, Iteration 3, cycle 2: `M_s` 269.94 -> 369.94 deg C, a
    wrong digit in the hundreds place. Cycle 1 of the same alloy records
    370.32 deg C, so the corrected value sits 0.38 deg C from it.
  - Ni36Ti20Cu12Co2Hf25Zr5, Iteration 2, cycle 2: `M_f` 229.30 -> 164.65 deg C.
    The published value was identical to that alloy's cycle-1 `A_s`, i.e.
    copied from the wrong cell.

  Both are documented under "Errata" in `data/README.md`. The corrections
  shift Table 5's aggregate rho_Ms from 0.429 to 0.439 (Iteration 3: 0.715 to
  0.733), MAE M_s from 64.69 to 64.28 deg C (Iteration 3: 44.26 to 43.10), MAE
  DeltaT from 34.36 to 33.13 deg C, and rho_DeltaT from 0.568 to 0.565.
  rho_Af, rho_DeltaH, MAE A_f, MAE DeltaH, the four-target counts (6/8/6 = 20)
  and the Pareto-front analysis including its 0.033 tail probability are all
  unchanged. `tests/expected_values.json` was updated to match.

  With both rows repaired, all 81 transforming alloys now satisfy the ordering
  filter, where 79 did before, so `scripts/train_tt_augmented.py` trains on 81
  campaign alloys rather than 79.

- `paper/2026-zadeh-htsma-R1.pdf`: refreshed to the build made from the
  corrected dataset, so the archived paper and the archived data agree. The
  previous bundle predated the corrections and still printed the superseded
  Table 5 values. Byte-identical to the two-column build in the manuscript
  repository; 43 pages, unchanged.

## [0.3.7] --- 2026-09-20

### Changed

- `paper/2026-zadeh-htsma-R1.pdf`: refreshed to the current build. The
  bibliography is now generated from `references.bib` via BibTeX rather than
  maintained inline, so the reference list gained two entries (Olier et al.
  1997 and Kai et al. 2019, cited in the Ti2Ni-type discussion) and the
  numbering changed throughout. The response to reviewers was updated to
  match.

## [0.3.6] --- 2026-09-20

### Added

- `paper/2026-zadeh-htsma-R1.pdf`: the revised manuscript (R1, clean
  two-column, no revision markup), so the archived bundle travels with the
  paper whose numbers it reproduces.

## [0.3.5] --- 2026-09-15

### Added

- `scripts/compute_pareto_membership.py`: reproduces the per-iteration
  Pareto-front membership of Section 3 and Appendix A.6 (fronts of 8 and 10
  alloys, 2/3/5 split, 3 earlier front alloys dominated, tail probability
  0.033). Hysteresis in this analysis is the midpoint A50 − M50 from the
  second DSC cycle, as stated in the revised manuscript. Tested in
  `tests/test_pareto_membership.py`.

## [0.3.4] --- 2026-09-15

### Added

- `scripts/compare_lambda2_ldt_models.py`: compares the composition-based
  λ2 model and the LDT transformation-strain model with values computed from
  the measured B2 and B19′ lattice parameters of the 70 alloys that have them,
  and reports the rank correlation between measured λ2 and DSC hysteresis
  (Section 3 and Appendix A.7 of the revised manuscript). Tested in
  `tests/test_lambda2_ldt_models.py`.

### Fixed

- README: Iteration 1 was K-medoid seeding of the CALPHAD-filtered
  candidates, not a Latin-hypercube batch; the ρ_Ms progression is 0.27 to
  0.72 (Table 5), not 0.25 to 0.73.

## [0.3.3] --- 2026-09-14

### Changed

- The supplementary ΔH analysis is now summarized in Appendix B of the revised
  manuscript. The README and the script docstring say so, instead of "not
  reported in the manuscript".

## [0.3.2] --- 2026-09-14

### Added

- `scripts/train_dh_on_campaign.py`: supplementary analysis, not reported in
  the manuscript, that trains ΔH models on the campaign's measured alloys and
  compares them with the ΔH predictions used during the campaign. A test runs a
  shortened version, and CI installs `catboost` and `scikit-learn` for it.

### Fixed

- Pin `pandas<3`. CBFV 1.1, which the vendored helper modules use to generate
  composition features, fails under pandas 3 (`TypeError: unhashable type:
  'StringArray'`); CI on Python 3.11 and 3.12 had started resolving pandas 3.0.

## [0.3.1] --- 2026-09-14

### Added

- Snapshot of `ML models/` from `sinazadeh/NiTi-alloy-discovery` (upstream
  `2e5ef7a`): the notebook and helper code used to select features for and
  train the transformation-temperature, hysteresis, and ΔH CatBoost models,
  and the Thermo-Calc templates used for CALPHAD screening. Training data and
  trained model files are not included.
- `requirements-ml.txt` for that notebook.
- Snapshot of `sinazadeh/CatBoost-SMAs` (upstream `224ef5d`), the
  transformation-temperature model and its literature dataset, so all three
  property predictors cited in the manuscript are archived here. A test checks
  its hyperparameters against Table B1.
- Tests that check the HEACalculator compatibility layer against the values
  of the HEACalculator copy used in the study.

### Fixed

- The vendored helper modules call `HEACalculator(formula, csv=True)`, an
  interface from an unreleased, locally modified HEACalculator 1.3.1.
  `HEACalculator>=2.0`, previously listed in `requirements.txt`, rejects the
  `csv` argument. A compatibility layer now provides identical values from the
  published HEACalculator 1.3.0, installed from its GitHub tag.

## [0.3.0] --- 2026-09-13

### Fixed

- Aligned the Table 5 surrogate-validation calculation with the DSC method by
  using second-cycle measurements while retaining one prediction set per
  alloy. Updated the reproduced rank correlations and absolute errors.
- Defined the four-target screening hysteresis consistently as second-cycle,
  stress-free DSC $\Delta T = A_f - M_s$. The corrected per-iteration joint
  pass counts are 6/29, 8/29, and 6/29 (20 alloys total); the combined
  BO-guided rate is 14/58 (24%).
- Corrected a co-author's given name to Cem Cakirhan in `CITATION.cff`.
- Wrote the champion-alloy formula in the fixed element order,
  `Ni46Ti28Co2Pd2Hf22`, in the README and scripts.

### Changed

- Re-executed the notebook so its outputs show the corrected values.

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
