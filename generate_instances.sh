#!/bin/bash
#SBATCH --mem=4G
#SBATCH --time=10:00
#SBATCH --partition=optimum
#SBATCH --output=python/examples/fixed_line/generating_test_files_slurm.out
#SBATCH --error=python/examples/fixed_line/generating_test_files_slurm.err

# Change to the correct working directory
cd /home/kollau/Recherche_Kolcheva/Simulator

# Load Conda and activate the SimulatorKolcheva environment
module load anaconda
conda activate SimulatorKolcheva

#Generate test files
python python/examples/stl_gtfs_parameter_parser_and_test_file_generator.py > python/examples/fixed_line/generating_test_files.out 2> python/examples/fixed_line/generating_test_files.err
