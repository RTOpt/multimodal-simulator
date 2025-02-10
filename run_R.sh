#!/bin/bash
#SBATCH --mem-per-cpu=16G
#SBATCH --time=72:00:00
#SBATCH --partition=optimumlong
#SBATCH --cpus-per-task=1
#SBATCH --output=python/examples/fixed_line/test_files_multi/R/slurm_output_%A_%a.out
#SBATCH --error=python/examples/fixed_line/test_files_multi/R/slurm_error_%A_%a.err
#SBATCH --array=0-11 # Dynamically adjust array range

# Change to the correct working directory
cd /home/kollau/Recherche_Kolcheva/Simulator

# Load Conda and activate the SimulatorKolcheva environment
source /home/kollau/.conda/envs/SimulatorKolcheva/bin/activate
# module load anaconda
# conda activate SimulatorKolcheva

# Run the specific test file for this array task
nohup python python/examples/fixed_line/test_files_multi/R/Test_${SLURM_ARRAY_TASK_ID}.py > python/examples/fixed_line/test_files_multi/R/output_${SLURM_ARRAY_TASK_ID}.out 2> python/examples/fixed_line/test_files_multi/R/error_${SLURM_ARRAY_TASK_ID}.err
conda deactivate
