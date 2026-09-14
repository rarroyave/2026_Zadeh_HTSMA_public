#!/bin/bash

# Slurm job template used by main.ipynb. Adapt resources to your cluster.
# Replace the email, module names/versions, and environment path before use.

#SBATCH --export=NONE # Do not propagate the submission environment
#SBATCH --get-user-env=L # Replicate the login environment
#SBATCH -J tcrun # Job Name
#SBATCH -t 3-0:00:00 # Wall time of 3 days
#SBATCH -N 1 # Request one node
#SBATCH --ntasks-per-node=48 # Request 48 cores per node
#SBATCH --mem=360G # Request 360 GB of memory per node
#SBATCH -o JobName.o%j # Standard output file
#SBATCH -e JobName.e%j # Standard error file

# Optional email notifications; replace the placeholder with your address.

#SBATCH --mail-type=ALL
#SBATCH --mail-user=<YOUR_EMAIL_ADDRESS>

# Purge all loaded modules to start with a clean environment
ml purge
ml "<COMPILER_MODULE>" "<THERMO_CALC_MODULE>" "<ANACONDA_MODULE>"
source activate "<CONDA_ENVIRONMENT_PATH>"

# (Optional) Set the path to the MPI PMI library, required for MPI usage
# export I_MPI_PMI_LIBRARY=/usr/lib64/libpmi.so

# Slurm provides the directory containing the submitted job.
cd "$SLURM_SUBMIT_DIR" || exit 1

# The notebook substitutes this exact command with the generated script name.
python filname.py
