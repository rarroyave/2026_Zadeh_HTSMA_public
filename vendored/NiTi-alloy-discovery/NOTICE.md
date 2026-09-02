# Vendored: NiTi-alloy-discovery (BO campaign engine)

This directory contains a snapshot of

- Upstream repository: https://github.com/sinazadeh/NiTi-alloy-discovery
- Upstream commit: `28dbc74b3d7dc4c3cb65ff9f694f8e69919b22ce`
- License: MIT (see `LICENSE` in this directory; the upstream repo did not
  carry an explicit license at snapshot time, so this MIT license is applied
  by the paper's author team, which owns the underlying work)

Vendored here so this reproducibility bundle is self-contained --- a
download from Zenodo does not depend on GitHub still hosting the upstream
repo.

## Primary code contributor

Danial Khatamsaz (`@author` header in `Iter2/main.py`).

## What was changed during vendoring

- `Iter2/all_space.csv` (top-level, ~128 MB) --- **stripped**. The top-level
  BO loop constructs `all_space` at runtime as
  `np.concatenate((feasibles, infeasibles))`, so this file was a redundant
  cache and is not needed to run `Iter2/main.py`.
- `Iter2/Probability_calculations/itr2/all_space.csv` (~128 MB) and
  `Iter3/Probability_calculations/itr3/all_space.csv` --- **not shipped**;
  regenerable from the design-space spec via `generate_design_space.py`
  (this directory) in ~15 s to produce the exact 3,812,408-row set that
  the sub-pipeline reads on line 33 of its `main.py`. To materialize:

  ```bash
  python generate_design_space.py > Iter2/Probability_calculations/itr2/all_space.csv
  python generate_design_space.py > Iter3/Probability_calculations/itr3/all_space.csv
  ```

  The generator was derived from Sina's Section 4.2.3 (Design Space
  Definition) and cross-validated as a byte-exact reproduction of the
  original CSV.
- `Iter3/Summary.pptx` (~4 MB) --- **stripped**. Personal working slide
  deck, not a reproducibility asset.

## Contents

- `Iter2/`, `Iter3/` --- per-iteration BO loop code plus tested-alloy
  outcomes, per-objective ground-truth values, and priors.
- `Iter{2,3}/main.py` --- BO loop entry point.
- `Iter{2,3}/gpModel.py`, `multiobjective.py`, `acquisitionFunc.py`,
  `reificationFusion.py` --- Gaussian-process surrogate, multi-objective
  acquisition, reification-based information fusion.
- `Iter{2,3}/Probability_calculations/` --- feasibility-probability
  modeling sub-pipeline that produces `feasibles.csv` / `infeasibles.csv`
  / `probs.csv` used by the top-level BO loop.
- `Iter{2,3}/postprocessing_analysis.m`, `data.mat`, `.fig` --- MATLAB
  post-processing artifacts (optional; not required for the Python BO
  loop).

## Running the BO loop

Install BO-specific dependencies alongside the analysis dependencies:

```bash
pip install -r ../../requirements.txt -r ../../requirements-bo.txt
```

Then, from `Iter2/` or `Iter3/`:

```bash
python main.py
```

To additionally rerun the feasibility-probability sub-pipeline (which trains
the model that produces `feasibles.csv` / `infeasibles.csv` / `probs.csv`):

```bash
cd Iter2/Probability_calculations/itr2   # or Iter3/.../itr3
python ../../generate_design_space.py > all_space.csv   # ~15 s, 128 MB
python main.py
```

Iteration 1 is not included: it was the initial design (Latin-hypercube
batch) that seeded the campaign and did not require the BO loop.

## Citation

If you use this Bayesian-optimization code or the per-iteration campaign
state, please cite the paper:

> Zadeh, S. H.; Broucek, J.; Cakirhan, C.; Li, M.; Khatamsaz, D.; Qian, X.;
> Karaman, I.; Arroyave, R. Bayesian-Optimization-Guided Discovery of
> NiTi(Co,Cu,Pd,Hf,Zr) Multi-Principal Element High-Temperature Shape
> Memory Alloys. *Acta Materialia* (2026, in review).
