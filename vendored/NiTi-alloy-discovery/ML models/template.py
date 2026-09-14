"""Template for batch Thermo-Calc equilibrium calculations.

The notebook inserts an input row slice and output filename for each job script.
Run generated scripts in an environment with a licensed TC-Python installation
and the TCNI12 database. Input compositions use atomic percentages and the
configured temperature uses degrees Celsius.
"""

import pandas as pd
from tc_python import TCPython
import os
import numpy as np
import io
from contextlib import redirect_stdout

# The notebook substitutes this exact statement with the row slice for each job.
composition_df = pd.read_csv("file.csv")

elements = ["Ni", "Ti", "Cu", "Hf", "Zr", "Pd", "Co"]
temperature = 950  # In Celsius


def get_phase_value(phase_name, stable_phases, result):
    """Return the phase mole fraction, using zero for absent phases."""
    if phase_name in stable_phases:
        return result.get_value_of(f"NPM({phase_name})")
    else:
        return 0


def calculate_composition(row, start, elements, temperature):
    """Calculate equilibrium for one composition and return the CSV result row."""
    calculation = (
        start.select_database_and_elements("TCNI12", elements)
        .get_system()
        .with_single_equilibrium_calculation()
        .set_condition("T", temperature + 273.15)
    )

    # Nickel is the dependent component; all other fractions are specified.
    for element in elements[1:]:
        element_weight = row.get(element, 0)  # Default to 0 if missing
        calculation = calculation.set_condition(f"X({element})", element_weight / 100)

    result = calculation.calculate()
    stable_phases = result.get_stable_phases()
    return [result.get_value_of(f"X({el})") * 100 for el in elements] + [
        get_phase_value("BCC_B2#1", stable_phases, result),
        get_phase_value("BCC_B2#2", stable_phases, result),
        get_phase_value("BCC_B2#3", stable_phases, result),
        get_phase_value("BCC_B2#4", stable_phases, result),
        get_phase_value("BCC_B2#5", stable_phases, result),
        get_phase_value("BCC_B2#6", stable_phases, result),
        get_phase_value("LIQUID#1", stable_phases, result),
        get_phase_value("LIQUID#2", stable_phases, result),
        get_phase_value("LIQUID#3", stable_phases, result),
        get_phase_value("FCC_L12#1", stable_phases, result),
        get_phase_value("FCC_L12#2", stable_phases, result),
        get_phase_value("SIGMA#1", stable_phases, result),
        get_phase_value("NI5ZR#1", stable_phases, result),
        get_phase_value("H_L21#1", stable_phases, result),
        get_phase_value("H_L21#2", stable_phases, result),
        get_phase_value("NI3TI_D024#1", stable_phases, result),
        get_phase_value("C14_LAVES#1", stable_phases, result),
        stable_phases,
        np.max(
            [
                result.get_value_of(f"NPM({phase})")
                for phase in stable_phases
                if phase in stable_phases
            ]
        ),
        result.get_value_of("T") - 273.15,
    ]


# Preserve existing results and write the header only for a new or empty file.
# The notebook substitutes every occurrence of the output filename below.
if not os.path.exists("tcresults_ct.csv") or os.path.getsize("tcresults_ct.csv") == 0:
    with open("tcresults_ct.csv", "w") as file:
        header = elements + [
            "BCC_B2#1",
            "BCC_B2#2",
            "BCC_B2#3",
            "BCC_B2#4",
            "BCC_B2#5",
            "BCC_B2#6",
            "LIQUID#1",
            "LIQUID#2",
            "LIQUID#3",
            "FCC_L12#1",
            "FCC_L12#2",
            "SIGMA#1",
            "NI5ZR#1",
            "H_L21#1",
            "H_L21#2",
            "NI3TI_D024#1",
            "C14_LAVES#1",
            "stable_phases",
            "max_val_stable_phase",
            "temperature(C)",
        ]
        file.write(",".join(header) + "\n")

# Flush rows in batches to limit memory use during larger composition searches.
batch_size = 100
results = []

trap = io.StringIO()
# Capture solver console output while collecting the structured phase results.
with redirect_stdout(trap), TCPython() as start:
    for index, row in composition_df.iterrows():
        try:
            results_row = calculate_composition(row, start, elements, temperature)
            results.append(results_row)

            # Save batch when it reaches the batch_size or on the last iteration
            if len(results) == batch_size or index == len(composition_df) - 1:
                pd.DataFrame(
                    results,
                    columns=[
                        "Ni",
                        "Ti",
                        "Cu",
                        "Hf",
                        "Zr",
                        "Pd",
                        "Co",
                        "BCC_B2#1",
                        "BCC_B2#2",
                        "BCC_B2#3",
                        "BCC_B2#4",
                        "BCC_B2#5",
                        "BCC_B2#6",
                        "LIQUID#1",
                        "LIQUID#2",
                        "LIQUID#3",
                        "FCC_L12#1",
                        "FCC_L12#2",
                        "SIGMA#1",
                        "NI5ZR#1",
                        "H_L21#1",
                        "H_L21#2",
                        "NI3TI_D024#1",
                        "C14_LAVES#1",
                        "stable_phases",
                        "max_val_stable_phase",
                        "temperature(C)",
                    ],
                ).round(2).to_csv(
                    "tcresults_ct.csv", mode="a", header=False, index=False
                )
                results = []  # Reset results list for the next batch
        except Exception as e:
            print(f"Error at index {index}: {e}")
