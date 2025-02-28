#!/bin/bash
#SBATCH --mem-per-cpu=16G
#SBATCH --time=72:00:00
#SBATCH --partition=optimumlong
#SBATCH --cpus-per-task=1
#SBATCH --output=python/examples/fixed_line/test_files_multi/Offline/slurm_output_%A_%a.out
#SBATCH --error=python/examples/fixed_line/test_files_multi/Offline/slurm_error_%A_%a.err
#SBATCH --array=0-2 # Dynamically adjust array range

# Change to the correct working directory
cd /home/kollau/Recherche_Kolcheva/Simulator

# Load Conda and activate the SimulatorKolcheva environment
module load anaconda
conda activate SimulatorKolcheva

# Get the list of test files
TEST_FILES=($(ls python/examples/fixed_line/test_files_multi/Offline/Test_*.py))

# Run the specific test file for this array task
nohup python python/examples/fixed_line/test_files_multi/Offline/Test_${SLURM_ARRAY_TASK_ID}.py > python/examples/fixed_line/test_files_multi/Offline/output_${SLURM_ARRAY_TASK_ID}.out 2> python/examples/fixed_line/test_files_multi/Offline/error_${SLURM_ARRAY_TASK_ID}.err

