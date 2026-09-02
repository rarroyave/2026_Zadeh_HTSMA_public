#!/bin/bash
##ENVIRONMENT SETTINGS; CHANGE WITH CAUTION
#SBATCH --export=NONE                #Do not propagate environment
#SBATCH --get-user-env=L             #Replicate login environment

##NECESSARY JOB SPECIFICATIONS
#SBATCH --job-name=P_eval
#SBATCH --time=100:00:00
#SBATCH --nodes=1                  
#SBATCH --ntasks-per-node=1
#SBATCH --mem=30G    
#SBATCH --output=output.%j

##OPTIONAL JOB SPECIFICATIONS
#SBATCH --account=132750963909
#SBATCH --mail-type=ALL 
#SBATCH --mail-user=danialkh26@tamu.edu


source /scratch/user/danialkh26/HTMDEC/htmdec/bin/activate
ml GCC/9.3.0 Python/3.8.2 
source /scratch/user/danialkh26/HTMDEC/htmdec/bin/activate
python main.py