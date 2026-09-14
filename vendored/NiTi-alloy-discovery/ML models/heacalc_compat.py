"""Compatibility layer for the HEACalculator interface used by helper.py.

The vendored helper modules call ``HEACalculator(formula, csv=True).get_csv_list()``.
That interface exists only in a locally modified HEACalculator 1.3.1 that was never
released; HEACalculator 2.x removed the ``csv`` argument. This wrapper provides the
same call on top of the published HEACalculator 1.3.0 and returns identical values
(see tests/test_heacalc_compat.py).

HEACalculator (Doguhan Sariturk, GPL-3.0) is not redistributed here. Install it with
    pip install --no-deps "HEACalculator @ git+https://github.com/dogusariturk/HEACalculator@v.1.3.0"
"""

import io
from contextlib import redirect_stdout

from HEACalculator import HEACalculator as _HEACalculator


class HEACalculator:
    """Wrap HEACalculator 1.3.0 and add the ``get_csv_list`` method of 1.3.1."""

    def __init__(self, formula, csv=False):
        with redirect_stdout(io.StringIO()):
            self._hea = _HEACalculator(formula)
        self.formula = self._hea.formula

    def get_csv_list(self):
        """Return the formula and nine properties formatted to two decimals."""
        h = self._hea
        values = [
            h.get_density(),
            h.get_atomic_size_difference(),
            h.get_omega(),
            h.get_gamma(),
            h.get_lambda(),
            h.get_valance_electron_concentration(),
            h.get_mixing_enthalpy(),
            h.get_mixing_entropy(),
            h.get_melting_temperature(),
        ]
        return [h.formula] + ["%.2f" % v for v in values]

    def __getattr__(self, name):
        return getattr(self._hea, name)
