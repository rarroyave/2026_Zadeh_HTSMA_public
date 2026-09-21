# Data dictionary --- `supplementary_data.xlsx`

The manuscript's Supplementary Information Excel workbook. 87 unique alloys
across three Bayesian-optimization iterations, all as-cast + homogenized and
characterized by DSC and UCFTC. Sheets:

| Sheet | Contents |
|---|---|
| `All Compiled Data` | 87 alloys x up to 2 DSC cycles each. Iteration, composition (Ni, Ti, Cu, Co, Pd, Hf, Zr in at.%), homogenization schedule (temp/time), DSC cycle number, DSC LCT/UCT (deg C), transforms flag (0/1), M_s, M_p, M_f, A_s, A_p, A_f (deg C), A->M and M->A enthalpies and average (J/g), XRD lattice parameters (a, b, c in nm; beta in deg) of B19' martensite and a0 of B2 austenite, ML-predicted M_s/M_f/A_s/A_f (deg C), ML-predicted enthalpy (J/g), free-form comments. Header row is row 40; preceding rows are the in-line column dictionary. |
| `Iteration 1/2/3 UCFTC` | 10 / 11 / 10 scaled-up alloys x multiple applied loads each. Full uniaxial constant-force thermal cycling per ASTM E3097: transformation temperatures M_s, M_f, A_s, A_f (deg C, with and without tangent correction) and their corresponding strains, LCT/UCT strains, initial/residual/transformation strains, M50/A50, thermal hysteresis (deg C). Header row is row 41. |

## Errata

Two rows of `All Compiled Data` recorded a martensite finish above the
martensite start (`M_f > M_s`), which is not physically possible. They were
the only two such rows out of 174. Both have been corrected against the raw
DSC traces by the author who produced the measurements, and both corrections
are single-cell transcription fixes.

### Ni50Ti25Hf19Zr6, Iteration 3, DSC cycle 2 --- `M_s` 269.94 -> 369.94

The row read

    M_s 269.94    M_f 332.19    A_s 422.13    A_f 442.42

and now reads

    M_s 369.94    M_f 332.19    A_s 422.13    A_f 442.42

A single digit was wrong in the hundreds place. Cycle 1 of the same alloy
records `M_s` 370.32, so the corrected cycle-2 value sits 0.38 deg C from it,
as expected between consecutive cycles.

### Ni36Ti20Cu12Co2Hf25Zr5, Iteration 2, DSC cycle 2 --- `M_f` 229.30 -> 164.65

The row read

    M_s 189.25    M_f 229.30    A_s 209.26    A_f 226.43

and now reads

    M_s 189.25    M_f 164.65    A_s 209.26    A_f 226.43

The published `M_f` was identical to the same alloy's cycle-1 `A_s` (229.30),
a value copied from the wrong cell. The correct figure was not recoverable
from the workbook and came from the raw data.

After both corrections no row in the workbook has `M_f > M_s`.

### Effect on the numbers reproduced by `scripts/`

| Quantity | Before | After |
| --- | ---: | ---: |
| Table 5 rho_Ms, all 81 alloys | 0.429 | 0.439 |
| Table 5 rho_Ms, Iteration 3 | 0.715 | 0.733 |
| MAE M_s, all 81 alloys (deg C) | 64.69 | 64.28 |
| MAE M_s, Iteration 3 (deg C) | 44.26 | 43.10 |
| MAE DeltaT, all 81 alloys (deg C) | 34.36 | 33.13 |
| Table 5 rho_DeltaT, all 81 alloys | 0.568 | 0.565 |

Unchanged: rho_Af, rho_DeltaH, MAE A_f, MAE DeltaH, the per-iteration
four-target counts (6/8/6 = 20), and the entire Pareto-front analysis
including the 0.033 tail probability. Neither corrected alloy is among the 31
strain-tested alloys the Pareto analysis uses, and `compute_four_pass_rates.py`
does not read `M_f` at all; the corrected `M_s` of 369.94 remains inside the
200--400 deg C window and its `A_f - M_s` of 72.5 deg C still exceeds the
50 deg C screen, so that alloy fails the same gate it failed before.

The workbook as originally published is recoverable with
`git show <commit>:data/supplementary_data.xlsx`.

## License

`supplementary_data.xlsx` is released under Creative Commons Attribution 4.0
International (CC BY 4.0). If you use it, please cite the paper.
