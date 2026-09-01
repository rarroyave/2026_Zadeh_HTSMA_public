# Data dictionary --- `supplementary_data.xlsx`

The manuscript's Supplementary Information Excel workbook. 87 unique alloys
across three Bayesian-optimization iterations, all as-cast + homogenized and
characterized by DSC and UCFTC. Sheets:

| Sheet | Contents |
|---|---|
| `All Compiled Data` | 87 alloys x up to 2 DSC cycles each. Iteration, composition (Ni, Ti, Cu, Co, Pd, Hf, Zr in at.%), homogenization schedule (temp/time), DSC cycle number, DSC LCT/UCT (deg C), transforms flag (0/1), M_s, M_p, M_f, A_s, A_p, A_f (deg C), A->M and M->A enthalpies and average (J/g), XRD lattice parameters (a, b, c in nm; beta in deg) of B19' martensite and a0 of B2 austenite, ML-predicted M_s/M_f/A_s/A_f (deg C), ML-predicted enthalpy (J/g), free-form comments. Header row is row 40; preceding rows are the in-line column dictionary. |
| `Iteration 1/2/3 UCFTC` | 10 / 11 / 10 scaled-up alloys x multiple applied loads each. Full uniaxial constant-force thermal cycling per ASTM E3097: transformation temperatures M_s, M_f, A_s, A_f (deg C, with and without tangent correction) and their corresponding strains, LCT/UCT strains, initial/residual/transformation strains, M50/A50, thermal hysteresis (deg C). Header row is row 41. |

## License

`supplementary_data.xlsx` is released under Creative Commons Attribution 4.0
International (CC BY 4.0). If you use it, please cite the paper.
