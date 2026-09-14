"""Composition features and crystallographic calculations used by main.ipynb.

Lattice parameters use angstroms, input angles use degrees, and transformation
strains are reported as percentages. Feature tables retain the notebook's
original column names so saved datasets remain compatible.

Code by Sina Zadeh, November 2023. Author website: <AUTHOR_WEBSITE>.
"""

import sympy as sp
import numpy as np
import pandas as pd
from CBFV import composition
from functools import reduce
import contextlib
import io
import logging
from heacalc_compat import HEACalculator  # vendoring patch, see NOTICE.md
import itertools


class DataHandler:
    """Wrap input records in the dataframe expected by the analysis pipeline."""

    def __init__(self, data):
        self.df = pd.DataFrame(data)

    def generate_dataframe(self):
        """Return the stored dataframe without copying it."""
        return self.df


class LambdaCalculator:
    """Calculate principal stretches from austenite and martensite lattice data."""

    def __init__(self, df):
        self.df = df

    @staticmethod
    def calculate_lambdas(a0, a, b, c, beta):
        """Return three ordered singular values, or NaNs if decomposition fails."""
        # Use ascending martensite lattice lengths throughout this workflow.
        a, b, c = sorted([a, b, c])
        B_matrix = np.array(
            [
                [a / a0, 0, (np.sqrt(2) * c * np.cos(np.radians(beta))) / (2 * a0)],
                [0, (np.sqrt(2) * b) / (2 * a0), 0],
                [0, 0, (np.sqrt(2) * c * np.sin(np.radians(beta))) / (2 * a0)],
            ]
        )
        try:
            _, singular_values, _ = np.linalg.svd(B_matrix, full_matrices=True)
            return np.sort(singular_values)
        except (ValueError, np.linalg.LinAlgError):
            return [np.nan, np.nan, np.nan]

    def generate_lambdas(self):
        """Append the three calculated stretches to each lattice-parameter row."""
        results = self.df.apply(
            lambda row: self.calculate_lambdas(
                row["a0 (A)"], row["a (A)"], row["b (A)"], row["c (A)"], row["beta"]
            ),
            axis=1,
            result_type="expand",
        )

        results.columns = [
            "lambda1_calculated",
            "lambda2_calculated",
            "lambda3_calculated",
        ]
        self.df = pd.concat([self.df, results], axis=1)
        return self.df


class Lambda2Model:
    """Apply the fitted descriptor threshold and linear lambda2 relations."""

    def __init__(self, df):
        self.df = df

    @staticmethod
    def determine_type_and_lambda(x):
        """Predict the transformation type and rounded lambda2 from a descriptor."""
        if x < 0.7:
            type_value = "B19'"
            central_lambda = 1.0333 * x + 0.2512
        elif x >= 0.7:
            type_value = "B19"
            central_lambda = 1.0333 * x + 0.2752

        return type_value, round(central_lambda, 3)

    def predict_transformation_and_lambda2(self):
        """Append model predictions and select summary columns when available."""
        type_lambda_df = self.df["jarvis_avg_first_ion_en_divi_voro_coord"].apply(
            self.determine_type_and_lambda
        )

        self.df["Predicted_Transformation_Type"] = type_lambda_df.apply(lambda x: x[0])
        self.df["Predicted_Lambda2"] = type_lambda_df.apply(lambda x: x[1])
        try:
            self.df = self.df[
                [
                    "composition",
                    "Alloy_System",
                    "jarvis_avg_first_ion_en_divi_voro_coord",
                    "Predicted_Transformation_Type",
                    "Predicted_Lambda2",
                ]
            ]
        except:
            # Preserve the full input schema when summary columns are unavailable.
            pass
        return self.df


class TransformationStrainCalculator:
    """Evaluate directional strains for the B19 and B19' correspondence variants."""

    def __init__(self):
        self.deformation_directions = None
        self.lattice_constants = None
        self.beta = None

    def set_custom_directions(self, deformation_directions):
        """Set the deformation-direction vector used in subsequent calculations."""
        self.deformation_directions = np.array(deformation_directions)

    def set_lattice_constants_and_beta(self, a0_val, a_val, b_val, c_val, beta_val):
        """Store lattice lengths and choose variants from the angle in degrees."""
        a, b, c = sorted([a_val, b_val, c_val])
        self.a0_val = a0_val
        self.a_val = a
        self.b_val = b
        self.c_val = c
        self.beta_val = np.deg2rad(beta_val) if beta_val is not None else None
        if self.beta_val == np.deg2rad(90.0):
            self.lattice_constants_sets = [
                ([1, 0, 0], [0, 1, 1], [0, -1, 1]),
                ([1, 0, 0], [0, -1, 1], [0, -1, -1]),
                ([0, 1, 0], [1, 0, 1], [1, 0, -1]),
                ([0, 1, 0], [1, 0, -1], [-1, 0, -1]),
                ([0, 0, 1], [1, 1, 0], [-1, 1, 0]),
                ([0, 0, -1], [1, -1, 0], [-1, -1, 0]),
            ]  # Reference DOI: 10.1016/j.pmatsci.2004.10.001
        else:
            self.lattice_constants_sets = [
                ([1, 0, 0], [0, 1, 1], [0, -1, 1]),
                ([-1, 0, 0], [0, -1, -1], [0, -1, 1]),
                ([1, 0, 0], [0, -1, 1], [0, -1, -1]),
                ([-1, 0, 0], [0, 1, -1], [0, -1, -1]),
                ([0, 1, 0], [1, 0, 1], [1, 0, -1]),
                ([0, -1, 0], [-1, 0, -1], [1, 0, -1]),
                ([0, 1, 0], [1, 0, -1], [-1, 0, -1]),
                ([0, -1, 0], [-1, 0, 1], [-1, 0, -1]),
                ([0, 0, 1], [1, 1, 0], [-1, 1, 0]),
                ([0, 0, -1], [-1, -1, 0], [-1, 1, 0]),
                ([0, 0, -1], [1, -1, 0], [-1, -1, 0]),
                ([0, 0, 1], [-1, 1, 0], [-1, -1, 0]),
            ]  # Reference DOI: 10.1016/j.pmatsci.2004.10.001

    def solve_equations(self, a_lc_1, a_lc_2, a_lc_3):
        """
        Solve the equations to determine the transformation matrix.

        Args:
            a_lc_1, a_lc_2, a_lc_3 (list or array-like): Lattice correspondence of austenite.

        Returns:
            sympy.Matrix: A 3x3 matrix representing the transformation matrix.

        Reference DOIs:
            10.1016/S1359-6454(02)00123-4
            10.1016/j.pmatsci.2004.10.001
        """
        B11, B12, B13, B21, B22, B23, B31, B32, B33 = sp.symbols(
            "B11 B12 B13 B21 B22 B23 B31 B32 B33"
        )

        # Equations based on the transformation and given conditions
        equations = [
            sp.Eq(
                B11 * self.a0_val * a_lc_1[0]
                + B12 * self.a0_val * a_lc_1[1]
                + B13 * self.a0_val * a_lc_1[2],
                self.a_val * sp.cos(self.beta_val),
            ),
            sp.Eq(
                B21 * self.a0_val * a_lc_1[0]
                + B22 * self.a0_val * a_lc_1[1]
                + B23 * self.a0_val * a_lc_1[2],
                self.a_val * sp.sin(self.beta_val),
            ),
            sp.Eq(
                B31 * self.a0_val * a_lc_1[0]
                + B32 * self.a0_val * a_lc_1[1]
                + B33 * self.a0_val * a_lc_1[2],
                0,
            ),
            sp.Eq(
                B11 * self.a0_val * a_lc_2[0]
                + B12 * self.a0_val * a_lc_2[1]
                + B13 * self.a0_val * a_lc_2[2],
                0,
            ),
            sp.Eq(
                B21 * self.a0_val * a_lc_2[0]
                + B22 * self.a0_val * a_lc_2[1]
                + B23 * self.a0_val * a_lc_2[2],
                0,
            ),
            sp.Eq(
                B31 * self.a0_val * a_lc_2[0]
                + B32 * self.a0_val * a_lc_2[1]
                + B33 * self.a0_val * a_lc_2[2],
                self.b_val,
            ),
            sp.Eq(
                B11 * self.a0_val * a_lc_3[0]
                + B12 * self.a0_val * a_lc_3[1]
                + B13 * self.a0_val * a_lc_3[2],
                self.c_val,
            ),
            sp.Eq(
                B21 * self.a0_val * a_lc_3[0]
                + B22 * self.a0_val * a_lc_3[1]
                + B23 * self.a0_val * a_lc_3[2],
                0,
            ),
            sp.Eq(
                B31 * self.a0_val * a_lc_3[0]
                + B32 * self.a0_val * a_lc_3[1]
                + B33 * self.a0_val * a_lc_3[2],
                0,
            ),
        ]

        # Solve the system of equations
        solutions = sp.solve(equations, (B11, B12, B13, B21, B22, B23, B31, B32, B33))

        # Create the solution matrix
        solution_matrix = sp.Matrix(
            [
                [solutions[B11], solutions[B12], solutions[B13]],
                [solutions[B21], solutions[B22], solutions[B23]],
                [solutions[B31], solutions[B32], solutions[B33]],
            ]
        )

        return solution_matrix

    @staticmethod
    def symbolic_matrix_to_numpy(sym_matrix):
        """Convert a symbolic solution matrix into a float64 NumPy array."""
        return np.array(sym_matrix).astype(np.float64)

    @staticmethod
    def calculate_transformation_strain(deformation_direction, B_np):
        """
        Calculate directional transformation strain as a percentage.

        Args:
            deformation_direction (numpy.ndarray): One-dimensional direction vector.
            B_np (numpy.ndarray): Two-dimensional transformation matrix.

        Returns:
            float: Change in vector length relative to its original length, in percent.

        Reference DOI:
            10.1016/j.actamat.2015.03.022
        """

        numerator = np.sqrt(
            deformation_direction.T @ B_np.T @ B_np @ deformation_direction
        )

        denominator = np.sqrt(deformation_direction.T @ deformation_direction)
        Eps = ((numerator / denominator) - 1) * 100
        return Eps

    def print_results(self):
        """Print the strain of each variant and the tensile/compressive extrema."""
        max_transformation_strain = -float("inf")
        # Initialize the minimum strain value
        min_transformation_strain = float("inf")

        print(f"Deformation direction: {self.deformation_directions}")

        Eps_values = []
        for a_lc_1, a_lc_2, a_lc_3 in self.lattice_constants_sets:
            solution_matrix = self.solve_equations(a_lc_1, a_lc_2, a_lc_3)
            B_np = self.symbolic_matrix_to_numpy(solution_matrix)
            Eps = self.calculate_transformation_strain(
                self.deformation_directions, B_np
            )
            Eps_values.append(Eps)

        max_transformation_strain = max(Eps_values)
        # Compute minimum strain for the current direction
        min_transformation_strain = min(Eps_values)

        variation_number = 1
        for i, Eps in enumerate(Eps_values):
            prime = "'" if i % 2 and self.beta_val != np.deg2rad(90.0) else ""
            variation_label = f"V{variation_number}{prime}"
            if Eps == max_transformation_strain:
                print(f"{variation_label}: {Eps:.5f}% <- Highest!")
            if Eps == min_transformation_strain:
                print(f"{variation_label}: {Eps:.5f}% <- Lowest!")
            else:
                print(f"{variation_label}: {Eps:.5f}%")

            if i % 2 or self.beta_val == np.deg2rad(90.0):
                variation_number += 1

        # Print the overall max and min strains
        tens_transformation_strain = [
            0 if max_transformation_strain < 0 else max_transformation_strain
        ][0]
        comp_transformation_strain = abs(
            [0 if min_transformation_strain > 0 else min_transformation_strain][0]
        )
        print(
            f"Maximum transformation strain for tension in direction {self.deformation_directions}: {tens_transformation_strain:.5f}% "
        )
        print(
            f"Maximum transformation strain for compression in direction {self.deformation_directions}: {comp_transformation_strain:.5f}% "
        )

    def calculate_tensile_transformation_strain(self, Eps_values):
        """Return the largest tensile strain, bounded below by zero."""
        max_transformation_strain = max(Eps_values)
        return max(0, max_transformation_strain)

    def calculate_compressive_transformation_strain(self, Eps_values):
        """Return the magnitude of the largest compressive strain, or zero."""
        min_transformation_strain = min(Eps_values)
        return abs(min(0, min_transformation_strain))

    def calc_max_strain_and_info(self):
        """Return tensile strain, compressive strain, and the configured direction."""
        Eps_values = []
        for a_lc_1, a_lc_2, a_lc_3 in self.lattice_constants_sets:
            solution_matrix = self.solve_equations(a_lc_1, a_lc_2, a_lc_3)
            B_np = self.symbolic_matrix_to_numpy(solution_matrix)
            Eps = self.calculate_transformation_strain(
                self.deformation_directions, B_np
            )
            Eps_values.append(Eps)

        tens_transformation_strain = self.calculate_tensile_transformation_strain(
            Eps_values
        )
        comp_transformation_strain = self.calculate_compressive_transformation_strain(
            Eps_values
        )

        max_strains_info = [
            (
                tens_transformation_strain,
                comp_transformation_strain,
                self.deformation_directions.tolist(),
            )
        ]
        return max_strains_info

    def calculate_max_strain_for_df(self, df):
        """Populate the legacy dataframe strain-summary columns in place."""
        # Prepare lists to store the new column data
        strain_maxs = []
        strain_texture_directions = []
        strain_deformation_directions = []
        strain_angle_degreeses = []

        for index, row in df.iterrows():
            # Set lattice constants and beta value for each row
            self.set_lattice_constants_and_beta(
                row["a0 (A)"], row["a (A)"], row["b (A)"], row["c (A)"], row["beta"]
            )

            # Calculate the maximum strain and related information
            max_strains_info = self.calc_max_strain_and_info()

            # Find the maximum strain among the calculated values
            max_strain_info = max(max_strains_info, key=lambda x: x[0])
            strain_max, deformation_direction, angle_degrees = max_strain_info

            # Append the results to the lists
            strain_maxs.append(strain_max)
            strain_deformation_directions.append(deformation_direction)
            strain_angle_degreeses.append(angle_degrees)

        # Append new columns to the DataFrame
        df["strain_max_theoretical"] = strain_maxs
        df["strain_texture_direction"] = strain_texture_directions
        df["strain_deformation_direction"] = strain_deformation_directions
        df["strain_angle_degrees"] = np.round(strain_angle_degreeses, 2)

        return df


class deformation_matrices:
    """Construct and display symbolic deformation matrices for both phase types."""

    B19p_vector_sets = [
        ([1, 0, 0], [0, 1, 1], [0, -1, 1]),
        ([-1, 0, 0], [0, -1, -1], [0, -1, 1]),
        ([1, 0, 0], [0, -1, 1], [0, -1, -1]),
        ([-1, 0, 0], [0, 1, -1], [0, -1, -1]),
        ([0, 1, 0], [1, 0, 1], [1, 0, -1]),
        ([0, -1, 0], [-1, 0, -1], [1, 0, -1]),
        ([0, 1, 0], [1, 0, -1], [-1, 0, -1]),
        ([0, -1, 0], [-1, 0, 1], [-1, 0, -1]),
        ([0, 0, 1], [1, 1, 0], [-1, 1, 0]),
        ([0, 0, -1], [-1, -1, 0], [-1, 1, 0]),
        ([0, 0, -1], [1, -1, 0], [-1, -1, 0]),
        ([0, 0, 1], [-1, 1, 0], [-1, -1, 0]),
    ]
    B19_vector_sets = [
        ([1, 0, 0], [0, 1, 1], [0, -1, 1]),
        ([1, 0, 0], [0, -1, 1], [0, -1, -1]),
        ([0, 1, 0], [1, 0, 1], [1, 0, -1]),
        ([0, 1, 0], [1, 0, -1], [-1, 0, -1]),
        ([0, 0, 1], [1, 1, 0], [-1, 1, 0]),
        ([0, 0, -1], [1, -1, 0], [-1, -1, 0]),
    ]

    def __init__(self):
        sp.init_printing(use_unicode=True)  # Initialize pretty printing

    def solve_equations(self, a_lc_1, a_lc_2, a_lc_3):
        """Solve the symbolic lattice correspondence for one variant."""
        B11, B12, B13, B21, B22, B23, B31, B32, B33, a0, a, b, c, beta = sp.symbols(
            "B11 B12 B13 B21 B22 B23 B31 B32 B33 a0 a b c beta"
        )

        eq1 = sp.Eq(
            B11 * a0 * a_lc_1[0] + B12 * a0 * a_lc_1[1] + B13 * a0 * a_lc_1[2],
            a * sp.cos(beta),
        )
        eq2 = sp.Eq(
            B21 * a0 * a_lc_1[0] + B22 * a0 * a_lc_1[1] + B23 * a0 * a_lc_1[2],
            a * sp.sin(beta),
        )
        eq3 = sp.Eq(
            B31 * a0 * a_lc_1[0] + B32 * a0 * a_lc_1[1] + B33 * a0 * a_lc_1[2], 0
        )

        eq4 = sp.Eq(
            B11 * a0 * a_lc_2[0] + B12 * a0 * a_lc_2[1] + B13 * a0 * a_lc_2[2], 0
        )
        eq5 = sp.Eq(
            B21 * a0 * a_lc_2[0] + B22 * a0 * a_lc_2[1] + B23 * a0 * a_lc_2[2], 0
        )
        eq6 = sp.Eq(
            B31 * a0 * a_lc_2[0] + B32 * a0 * a_lc_2[1] + B33 * a0 * a_lc_2[2], b
        )

        eq7 = sp.Eq(
            B11 * a0 * a_lc_3[0] + B12 * a0 * a_lc_3[1] + B13 * a0 * a_lc_3[2], c
        )
        eq8 = sp.Eq(
            B21 * a0 * a_lc_3[0] + B22 * a0 * a_lc_3[1] + B23 * a0 * a_lc_3[2], 0
        )
        eq9 = sp.Eq(
            B31 * a0 * a_lc_3[0] + B32 * a0 * a_lc_3[1] + B33 * a0 * a_lc_3[2], 0
        )

        solutions = sp.solve(
            (eq1, eq2, eq3, eq4, eq5, eq6, eq7, eq8, eq9),
            (B11, B12, B13, B21, B22, B23, B31, B32, B33),
        )

        if isinstance(solutions, dict):
            return sp.Matrix(
                [
                    [solutions[B11], solutions[B12], solutions[B13]],
                    [solutions[B21], solutions[B22], solutions[B23]],
                    [solutions[B31], solutions[B32], solutions[B33]],
                ]
            )
        else:
            return None

    def print_B19p(self):
        """Display the twelve B19' matrices with paired variant labels."""
        solution_matrices = []
        for vectors in self.B19p_vector_sets:
            solution = self.solve_equations(*vectors)
            if solution is not None:
                solution_matrices.append(solution)
            else:
                solution_matrices.append("No unique solution")
        print("B19':")
        for i, solution_matrix in enumerate(solution_matrices):
            label = f"V{(i // 2) + 1}" + ("'" if i % 2 else "")
            print(f"{label}:")
            if isinstance(solution_matrix, str):
                print(solution_matrix)
            else:
                print(sp.pretty(solution_matrix))
            print()  # Newline for readability

    def print_B19(self):
        """Display the six B19 matrices with their variant labels."""
        solution_matrices = []
        for vectors in self.B19_vector_sets:
            solution = self.solve_equations(*vectors)
            if solution is not None:
                solution_matrices.append(solution)
            else:
                solution_matrices.append("No unique solution")
        print("B19:")
        for i, solution_matrix in enumerate(solution_matrices):
            label = f"V{(i+1)}"
            print(f"{label}:")
            if isinstance(solution_matrix, str):
                print(solution_matrix)
            else:
                print(sp.pretty(solution_matrix))
            print()  # Newline for readability


class FeatureGenerator:
    """Build formula strings and composition descriptors from element columns.

    Generate composition formulas before requesting descriptor features. The
    reduced feature method returns the lambda2 model input; the full method adds
    CBFV, HEA, and arithmetic combination features.
    """

    # Keep the alloy-system labels consistent with the original analysis tables.
    replacements = {
        "CuMoNiTi": "NiTiCuMo",
        "CuHfNiPdTiZr": "NiTiCuHfPdZr",
        "PdTiVZr": "PdTiZrV",
        "AlCuNiTi": "NiTiAlCu",
        "CuNiPtTi": "NiTiCuPt",
        "AlNiTiZr": "NiTiZrAl",
        "CuNiSiTi": "NiTiCuSi",
        "HfNiSnTi": "NiTiHfSn",
        "NiPbTiZr": "NiTiPbZr",
        "CuHfNiPbTi": "NiTiHfCuPb",
        "CoNiPbTi": "NiTiCoPb",
        "CuNiPbTiZr": "NiTiCuZrPb",
        "CuHfNiPbTiZr": "NiTiCuHfPbZr",
        "AuCuNiTi": "NiTiCuAu",
        "CuNiPdTi": "NiTiPdCu",
        "NiPdPtTi": "NiTiPdPt",
        "NbNiTiZr": "NiTiNbZr",
        "HfNiTiZr": "NiTiHfZr",
        "NiPdTaTi": "NiTiPdTa",
        "CuHfNiTi": "NiTiHfCu",
        "CuHfNiTiZr": "NiTiHfZrCu",
        "BNiPdTi": "NiTiPdB",
        "BNiTiZr": "NiTiZrB",
        "CoCuNiTi": "NiTiCuCo",
        "CoInMnNi": "NiMnCoIn",
        "CoNiPdTi": "NiTiPdCo",
        "CuFeHfNiTi": "NiTiHfFeCu",
        "NiPdScTi": "NiTiPdSc",
        "HfNiTaTi": "NiTiHfTa",
        "CuNbNiTi": "NiTiCuNb",
        "CuNiTiZr": "NiTiCuZr",
        "HfNiPdTi": "NiTiPdHf",
        "CuNiTi": "NiTiCu",
        "NiPtTi": "NiTiPt",
        "HfNiTi": "NiTiHf",
        "NbNiTi": "NiTiNb",
        "NiPdTi": "NiTiPd",
        "NiTaTi": "NiTiTa",
        "NiReTi": "NiTiRe",
        "NiSiTi": "NiTiSi",
        "NiSnTi": "NiTiSn",
        "NiSbTi": "NiTiSb",
        "NiScTi": "NiTiSc",
        "NiTeTi": "NiTiTe",
        "NiPbTi": "NiTiPb",
        "NiPrTi": "NiTiPr",
        "AuNiTi": "NiTiAu",
        "NdNiTi": "NiTiNd",
        "NiRhTi": "NiTiRh",
    }

    def __init__(self, df):
        self.df = df.copy()
        self.ext_df = df.copy()
        self.columns_range = self.df.columns
        self.base_features_generated = False

    @staticmethod
    def stringify(x):
        """Format nonzero amounts for a composition string; omit missing values."""
        return str(float(x)) if pd.notnull(x) and x != 0 else ""

    @staticmethod
    def is_almost_zero(num):
        """Apply the tolerance used when reducing floating-point element ratios."""
        return abs(num) < 1e-9

    @staticmethod
    def greatest_common_divisor(a, b):
        """Reduce two element amounts using the workflow's numerical tolerance."""
        return (
            a
            if FeatureGenerator.is_almost_zero(b)
            else FeatureGenerator.greatest_common_divisor(b, a % b)
        )

    def gcd_of_array(self, array):
        """Find the common factor shared by a sequence of element amounts."""
        return reduce(self.greatest_common_divisor, array)

    def correct_ratios(self, arr_values):
        """Convert element amounts to rounded integer formula ratios."""
        gcd = self.gcd_of_array(arr_values)
        return [round(a / gcd) for a in arr_values]

    def to_formula_string(self, dct):
        """Join nonzero element ratios into a reduced formula string."""
        corrected_vals = self.correct_ratios(list(dct.values()))
        elements = [
            element for element, value in zip(dct.keys(), corrected_vals) if value != 0
        ]
        values = [value for value in corrected_vals if value != 0]
        return "".join(
            [f"{element}{value}" for element, value in zip(elements, values)]
        )

    def generate_combinations(self, main_elements=None):
        """Generate sums, differences, and optional ratios of element columns."""
        # Create a copy of the original DataFrame to ensure it doesn't get modified
        df_copy = self.df.copy()

        # Coerce nonnumeric values to NaN before combining element amounts.
        df_copy = df_copy.apply(pd.to_numeric, errors="coerce")

        # Get all element columns
        elements = list(df_copy.columns)

        # If main_elements are specified, filter the element list
        if main_elements is not None:
            elements = [element for element in elements if element in main_elements]

        # Create a dictionary to store new columns
        new_columns = {}

        # Generate all possible combinations of the specified elements
        for r in range(2, len(elements) + 1):
            for combination in itertools.combinations(elements, r):
                # Generate both addition and subtraction columns for each combination
                for signs in itertools.product(["+", "-"], repeat=len(combination) - 1):
                    col_name = combination[0]
                    expression = f"df_copy['{combination[0]}']"

                    for i, sign in enumerate(signs):
                        col_name += f"{sign}{combination[i + 1]}"
                        expression += f" {sign} df_copy['{combination[i + 1]}']"

                    # Expressions are built from the dataframe's element-column names.
                    try:
                        new_columns[col_name] = eval(expression)
                    except Exception as e:
                        new_columns[col_name] = np.nan

        # Concatenate all new columns to the original DataFrame copy at once
        new_columns_df = pd.DataFrame(new_columns)
        df_copy = pd.concat([df_copy, new_columns_df], axis=1)

        # Add ratios for specified main elements divided by all generated columns at once to avoid fragmentation
        ratio_columns = {}
        generated_columns = list(new_columns_df.columns)
        if main_elements is not None:
            for element in main_elements:
                for column in generated_columns:
                    ratio_columns[f"{element}/{column}"] = (
                        df_copy[element] / df_copy[column]
                    )

        ratio_columns_df = pd.DataFrame(ratio_columns)
        df_copy = pd.concat([df_copy, ratio_columns_df], axis=1)

        return df_copy

    def generate_composition_formula(self):
        """Add composition strings and reduced formulas from the input columns."""
        self.df["composition"] = (
            self.df[self.columns_range]
            .apply(lambda x: x.map(self.stringify))
            .apply(
                lambda row: "".join(
                    [f"{k}{v}" for k, v in row.items() if v != "" and v != "0.0"]
                ),
                axis=1,
            )
        )

        dict_alloy_compositions = self.df[self.columns_range].to_dict("split")
        formula_list = [
            self.to_formula_string(
                dict(zip(dict_alloy_compositions["columns"], row_data))
            )
            for row_data in dict_alloy_compositions["data"]
        ]
        self.df["formula"] = formula_list
        return self.df

    def generate_features(self):
        """Return composition metadata and the JARVIS descriptor used by lambda2."""
        self.df["Alloy_System"] = (
            self.df["formula"]
            .replace(r"\d+", "", regex=True)
            .replace(FeatureGenerator.replacements, regex=True)
        )
        self.df["niti_base"] = self.df.Alloy_System.apply(
            lambda x: "True" if "NiTi" in x else "False"
        )
        temp_df = self.df.copy()

        self.df["target"] = 0
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            logging.getLogger().setLevel(logging.CRITICAL)

            X_jarvis, _, _, _ = composition.generate_features(
                self.df, elem_prop="jarvis", sum_feat=False
            )
        self.df = pd.concat(
            [
                self.ext_df,
                X_jarvis.add_prefix("jarvis_"),
                temp_df["Alloy_System"],
                temp_df["composition"],
                temp_df["formula"],
            ],
            axis=1,
        )
        self.df = self.df[
            [
                "composition",
                "formula",
                "Alloy_System",
                "jarvis_avg_first_ion_en_divi_voro_coord",
            ]
        ]
        return self.df

    def generate_features_all(self, main_elements):
        """Combine elemental, arithmetic, CBFV, and HEA descriptors for all rows."""
        # Generate combinations of elements first
        combinations_df = self.generate_combinations(main_elements=main_elements)
        # Generate alloy system
        self.df["Alloy_System"] = (
            self.df.formula.replace(r"\d+", "", regex=True)
            .replace("AlNiTiZr", "NiTiZrAl")
            .replace("NiRhTi", "NiTiRh")
            .replace("CuNiPdTi", "NiTiPdCu")
            .replace("NiPdPtTi", "NiTiPdPt")
            .replace("NbNiTiZr", "NiTiNbZr")
            .replace("HfNiTiZr", "NiTiHfZr")
            .replace("NiPdTaTi", "NiTiPdTa")
            .replace("CuNiTi", "NiTiCu")
            .replace("NiPtTi", "NiTiPt")
            .replace("HfNiTi", "NiTiHf")
            .replace("AuCuNiTi", "NiTiCuAu")
            .replace("AuNiTi", "NiTiAu")
            .replace("BNiPdTi", "NiTiPdB")
            .replace("BNiTiZr", "NiTiZrB")
            .replace("CoCuNiTi", "NiTiCuCo")
            .replace("CoInMnNi", "NiMnCoIn")
            .replace("CoNiPdTi", "NiTiPdCo")
            .replace("CuFeHfNiTi", "NiTiHfFeCu")
            .replace("CuHfNiTi", "NiTiHfCu")
            .replace("CuHfNiTiZr", "NiTiHfZrCu")
            .replace("CuNbNiTi", "NiTiCuNb")
            .replace("CuNiTiZr", "NiTiCuZr")
            .replace("HfNiPdTi", "NiTiPdHf")
            .replace("NbNiTi", "NiTiNb")
            .replace("NiPdScTi", "NiTiPdSc")
            .replace("NiPdTi", "NiTiPd")
            .replace("NiTaTi", "NiTiTa")
            .replace("HfNiTaTi", "NiTiHfTa")
            .replace("NiReTi", "NiTiRe")
            .replace("NiSiTi", "NiTiSi")
            .replace("NiSnTi", "NiTiSn")
            .replace("NiSbTi", "NiTiSb")
            .replace("NiScTi", "NiTiSc")
            .replace("NiTeTi", "NiTiTe")
            .replace("NiPbTi", "NiTiPb")
            .replace("NiPrTi", "NiTiPr")
            .replace("CuNiSiTi", "NiTiCuSi")
            .replace("HfNiSnTi", "NiTiHfSn")
            .replace("NiPbTiZr", "NiTiPbZr")
            .replace("CuHfNiPbTi", "NiTiHfCuPb")
            .replace("CoNiPbTi", "NiTiCoPb")
            .replace("CuNiPbTiZr", "NiTiCuZrPb")
            .replace("CuHfNiPbTiZr", "NiTiCuHfPbZr")
        )
        self.df["niti_base"] = self.df.Alloy_System.apply(
            lambda x: "True" if "NiTi" in x else "False"
        )
        temp_df = self.df.copy()

        # Generate HEA related features
        lst = []
        for alloy in temp_df["composition"]:
            lst.append(HEACalculator(alloy, csv=True).get_csv_list())
        headers = [
            "Formula",
            "Density",
            "Delta",
            "Omega",
            "Gamma",
            "lambda",
            "VEC",
            "Mixing Enthalpy",
            "Mixing Entropy",
            "Melting Temperature",
        ]
        hea_features_df = pd.DataFrame(lst, columns=headers).iloc[:, 1:]

        # Generate compositional features
        self.df["target"] = 0

        X_jarvis, _, _, _ = composition.generate_features(
            self.df, elem_prop="jarvis", sum_feat=True
        )
        X_magpie, _, _, _ = composition.generate_features(
            self.df, elem_prop="magpie", sum_feat=True
        )
        X_oliynyk, _, _, _ = composition.generate_features(
            self.df, elem_prop="oliynyk", sum_feat=True
        )
        X_mat2vec, _, _, _ = composition.generate_features(
            self.df, elem_prop="mat2vec", sum_feat=True
        )
        X_onehot, _, _, _ = composition.generate_features(
            self.df, elem_prop="onehot", sum_feat=True
        )
        self.df = pd.concat(
            [
                self.ext_df,
                X_jarvis.add_prefix("jarvis_"),
                X_magpie.add_prefix("magpie_"),
                X_oliynyk.add_prefix("oliynyk_"),
                X_mat2vec.add_prefix("mat2vec_"),
                X_onehot.add_prefix("onehot_"),
                hea_features_df.add_prefix("hea_"),
                combinations_df.add_prefix("comb_"),
            ],
            axis=1,
        )
        return self.df
