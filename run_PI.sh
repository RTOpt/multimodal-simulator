#!/bin/bash
#SBATCH --mem-per-cpu=8G
#SBATCH --time==47:59:00
#SBATCH --partition=optimum
#SBATCH --cpus-per-task=2
#SBATCH --output=python/examples/fixed_line/test_files_multi/PI/slurm_output_%A_%a.out
#SBATCH --error=python/examples/fixed_line/test_files_multi/PI/slurm_error_%A_%a.err
#SBATCH --array=0-11 # Dynamically adjust array range

# Change to the correct working directory
cd /home/kollau/Recherche_Kolcheva/Simulator

# Load Conda and activate the SimulatorKolcheva environment
module load anaconda
conda activate SimulatorKolcheva

# Run the specific test file for this array task
nohup python python/examples/fixed_line/test_files_multi/PI/Test_${SLURM_ARRAY_TASK_ID}.py > python/examples/fixed_line/test_files_multi/PI/output_${SLURM_ARRAY_TASK_ID}.out 2> python/examples/fixed_line/test_files_multi/PI/error_${SLURM_ARRAY_TASK_ID}.err

