# Vendored: Phase-Compatibility-Model-NiTi

This directory contains a verbatim snapshot of

- Repository: https://github.com/sinazadeh/Phase-Compatibility-Model-NiTi
- Commit: `a1b4fd889b2a6ee7c7857a4d4e29fd7007e67923`
- License: MIT (see `LICENSE` in this directory)

Vendored here so this reproducibility bundle is self-contained --- a
download from Zenodo does not depend on GitHub still hosting the upstream
repo.

For updates, bug reports, or feature requests, please open an issue on the
upstream repository rather than modifying this vendored copy.

## Citation

> S. Hossein Zadeh, C. Cakirhan, D. Khatamsaz, J. Broucek, T.D. Brown,
> X. Qian, I. Karaman, R. Arroyave, "Data-driven study of
> composition-dependent phase compatibility in NiTi shape memory alloys,"
> Mater. Des. 244 (2024) 113096.
> https://doi.org/10.1016/j.matdes.2024.113096

## Local patch (v0.3.1)

`helper.py` imports `HEACalculator` from `heacalc_compat.py` (this directory)
instead of from the HEACalculator package. The helper calls
`HEACalculator(formula, csv=True).get_csv_list()`, which no published
HEACalculator release provides; the compatibility layer supplies it on top of
HEACalculator 1.3.0 with identical values. Install HEACalculator 1.3.0 with
`pip install --no-deps "HEACalculator @ git+https://github.com/dogusariturk/HEACalculator@v.1.3.0"`.
