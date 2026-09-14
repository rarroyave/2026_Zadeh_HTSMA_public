# Vendored: CatBoost-SMAs (transformation-temperature model)

This directory contains a snapshot of

- Upstream repository: https://github.com/sinazadeh/CatBoost-SMAs
- Upstream commit: `224ef5dff0631f69abbc8ef886c98ea2ee9cf581`
- License: MIT (see `LICENSE`, copied from upstream; Copyright (c) 2023 Sina
  Hossein Zadeh)

Vendored here so this reproducibility bundle is self-contained --- a download
from Zenodo does not depend on GitHub still hosting the upstream repo.

## What was changed during vendoring

Nothing. All four files are byte-identical to the upstream commit.

## Contents

- `main.py` --- cleans the literature data, builds CBFV `jarvis` composition
  features with alloy-family flags and processing descriptors, splits the data
  80/20 (`random_state=42`), and trains a multi-output CatBoost model
  (`MultiRMSE`) for Ms, Mf, As, and Af. Its hyperparameters are those listed in
  Table B1 of the manuscript (`tests/test_vendored_models.py` checks this).
- `raw_data.csv` --- 4,900 literature records. `main.py` keeps the 1,811 with
  all four transformation temperatures, physically ordered temperatures, and
  compositions summing to 100 at.%.
- `README.md`, `LICENSE` --- from upstream.

Upstream provides no trained model file; `main.py` retrains the model.

## Running

`main.py` needs the software versions it was written for. With pandas 2.x,
CBFV's `extend_features` step fails because it takes the median of text
columns. It runs unchanged in the following environment (tested 2026-09-14,
about 2.5 minutes on a laptop):

```bash
uv venv --python 3.10 venv310 && . venv310/bin/activate
uv pip install "numpy==1.23.5" "pandas==1.5.3" "scikit-learn==1.2.2" \
    "catboost==1.0.6" "CBFV==1.1.0" "setuptools<81"
python main.py
```

That run trains on the 1,689 records whose composition occurs more than once
(single-occurrence compositions are held out by the script) and reports, on
its 20% test split:

| Metric | This run | Published (manuscript Section 2.5) |
| --- | ---: | ---: |
| RMSE | 24.7 °C | 25.1 °C |
| MAE | 17.0 °C | 17.4 °C |
| R² | 0.936 | 0.95 |

The values are close to, but not identical with, the published ones. The
script does not set a CatBoost random seed, and library builds differ from the
original environment; the difference was not investigated further.

## Relation to the manuscript

This is the published transformation-temperature model of Hossein Zadeh et
al., *Comput. Mater. Sci.* 226 (2023) 112225, cited in Section 2.5 of the
manuscript. During the campaign this predictor was retrained after each
iteration with the newly measured alloys appended (Section 2.4.1).

## Citation

> S. Hossein Zadeh, A. Behbahanian, J. Broucek, M. Fan, G. Vazquez, M. Noroozi,
> W. Trehern, X. Qian, I. Karaman, R. Arroyave, An interpretable boosting-based
> predictive model for transformation temperatures of shape memory alloys,
> *Comput. Mater. Sci.* 226 (2023) 112225.
> https://doi.org/10.1016/j.commatsci.2023.112225
