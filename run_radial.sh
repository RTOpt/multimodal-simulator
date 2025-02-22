#!/bin/bash
#SBATCH --mem-per-cpu=16G
#SBATCH --time=15:00:00
#SBATCH --partition=optimum
#SBATCH --cpus-per-task=1
#SBATCH --output=python/examples/fixed_line/test_files_multi_radial/slurm_output_%A_%a.out
#SBATCH --error=python/examples/fixed_line/test_files_multi_radial/slurm_error_%A_%a.err
#SBATCH --array=0-12  # 13 tasks for 13 test files

# Change to the correct working directory
cd /home/kollau/Recherche_Kolcheva/Simulator

# Load Conda and activate the environment
source /home/kollau/.conda/envs/SimulatorKolcheva/bin/activate

# Define the base directory
BASE_DIR="python/examples/fixed_line/test_files_multi_radial"

# Manually define the list of test files (ensure this is in correct order)
TEST_FILES=(
    "$BASE_DIR/D/Test_0.py" "$BASE_DIR/D/Test_1.py" "$BASE_DIR/D/Test_2.py" "$BASE_DIR/D/Test_3.py"
    "$BASE_DIR/Offline/Test_0.py"
    "$BASE_DIR/PI/Test_0.py" "$BASE_DIR/PI/Test_1.py" "$BASE_DIR/PI/Test_2.py" "$BASE_DIR/PI/Test_3.py"
    "$BASE_DIR/R/Test_0.py" "$BASE_DIR/R/Test_1.py" "$BASE_DIR/R/Test_2.py" "$BASE_DIR/R/Test_3.py"
)

# Select the test file corresponding to this SLURM task
FILE_TO_RUN=${TEST_FILES[$SLURM_ARRAY_TASK_ID]}

# Extract the subfolder and file index
SUB_DIR=$(dirname "$FILE_TO_RUN")
FILE_INDEX=$(basename "$FILE_TO_RUN" | sed 's/Test_\([0-9]*\)\.py/\1/')

# Print debug information
echo "Running file: $FILE_TO_RUN"
echo "SLURM Task ID: $SLURM_ARRAY_TASK_ID"

# Run the test file and save output/error logs in its corresponding folder
python "$FILE_TO_RUN" > "$SUB_DIR/output_${FILE_INDEX}.out" 2> "$SUB_DIR/error_${FILE_INDEX}.err"

# Deactivate the Conda environment
conda deactivate
#end of file