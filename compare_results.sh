#!/bin/bash
#SBATCH --mem=10G
#SBATCH --time=10:00
#SBATCH --partition=optimum
#SBATCH --output=python/examples/python/examples/fixed_line/solution_comparison_slurm_output_%A_%a.out
#SBATCH --error=python/examples/python/examples/fixed_line/solution_comparison_slurm_error_%A_%a.err

# Change to the correct working directory
cd /home/kollau/Recherche_Kolcheva/Simulator

# Load Conda and activate the SimulatorKolcheva environment
module load anaconda
conda activate SimulatorKolcheva

# Run the specific test file for this array task
nohup python python/examples/python/examples/stl_gtfs_transfer_synchro_solution_comparison.py > python/examples/fixed_line/slurm_transfer_synchro_solution_comparison.out 2> python/examples/fixed_line/slurm_transfer_synchro_solution_comparison.err

