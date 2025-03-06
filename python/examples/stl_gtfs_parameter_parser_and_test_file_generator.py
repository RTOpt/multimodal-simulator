import sys
import os
import json
from itertools import product
from fixed_line.stl_network_analysis import get_route_dictionary

sys.path.append(os.path.abspath('../../..'))
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
sys.path.append(r"/home/kollau/Recherche_Kolcheva/Simulator/python/examples")

def keep_routes_to_optimize(Case):
    """ Reads the test_trip_dir.json file containing all routes to keep for the optimization and returns a list of valid routes to optimize. """

    completename = os.path.join('data','fixed_line','gtfs', 'test_trip_dir.json')
    with open(completename, 'r') as fp:
        dict = json.load(fp)
    fp.close()
    for case in Case:
        all_ligns = Case[case]['ligns']
        all_dirs = Case[case]['dirs']
        for lign in all_ligns:
            for dir in all_dirs:
                if lign not in dict:
                    print(f"Route {lign} not found in test_trip_dir.json")
                    all_ligns.remove(lign)
                    break
                else: 
                    if dir not in dict[lign]:
                        print(f"Route {lign}{dir} not found in test_trip_dir.json")
                        all_ligns.remove(lign)
                        break
    return Case

def parse_parameters_for_transfer_synchro(network_style = ''):
    all_ligns_SN= ['151', '17', '27', '33', '37', '41', '43', '45', '46', '55', '61', '63', '65', '901', '902', '903', '925']
    all_ligns_EO= ['144', '20', '222', '22', '24','252', '26', '42', '52', '56', '60', '66', '70', '74', '76', '942']
    Case={}
    Case['EO']={}
    Case['EO']['ligns']=all_ligns_EO
    Case['EO']['dirs']=['E','O']
    Case['SN']={}
    Case['SN']['ligns']=all_ligns_SN
    Case['SN']['dirs']=['S','N']
    Case = keep_routes_to_optimize(Case)
    
    index = {}
    all_lines_indiv = []
    for i in range(4):
        index[i] = 0
    index_multi = {}
    for i in range(4):
        index_multi[i] = 0
    combinations = {}
    combinations_multi = {}
    for case in Case:
        ligns = Case[case]['ligns']
        dirs = Case[case]['dirs']
        all_lines_indiv.extend([lign+dir for lign, dir in product(ligns, dirs)])
    if network_style != '':
        print('network_style:', network_style)
        all_lines_indiv = get_route_dictionary()[network_style]
    # print(all_lines_indiv)
    if network_style == '':
        params = {
                "algo": [0, 1, 2, 3],
                "sp": [False, True],
                "ss": [False, True],
                'dates': [25, 26, 27]
            }
    else:
        params = {
                "algo": [0, 1, 2, 3],
                "sp": [False, True],
                "ss": [False, True],
                'dates': [25]
            }
    keys = list(params.keys())
    values = list(params.values())

    #Create a list with : all individual lines
    routes_to_optimize_names=[]
    for route_name in all_lines_indiv:
        routes_to_optimize_names.append([route_name,])
    # print(routes_to_optimize_names)
    # Generate combinations with other parameters
    other_combinations = list(product(*values))

    # Single line combinations
    for i, (routes_to_optimize_name, other_combination) in enumerate(product(routes_to_optimize_names, other_combinations)):
        algo = int(other_combination[keys.index('algo')])
        if algo == 0 and (bool(other_combination[keys.index('sp')]) == True or bool(other_combination[keys.index('ss')]) == True):
            continue
        combination_name = 'Combination{}_{}'.format(algo, index[algo])
        combinations[combination_name] = {
            'routes_to_optimize_names': routes_to_optimize_name,
            'algo': algo,
            'sp': other_combination[keys.index('sp')],
            'ss': other_combination[keys.index('ss')],
            'date': other_combination[keys.index('dates')],
            'index': index[algo]
        }
        index[algo] += 1
    
    # Multi line combinations
    routes_to_optimize_names = all_lines_indiv
    for i, other_combination in enumerate(other_combinations):
        algo = int(other_combination[keys.index('algo')])
        if algo == 0 and (bool(other_combination[keys.index('sp')]) == True or bool(other_combination[keys.index('ss')]) == True):
            continue
        combination_name = 'Combination{}_{}'.format(algo, index_multi[algo])
        combinations_multi[combination_name] = {
            'routes_to_optimize_names': routes_to_optimize_names,
            'algo': other_combination[keys.index('algo')],
            'sp': other_combination[keys.index('sp')],
            'ss': other_combination[keys.index('ss')],
            'date': other_combination[keys.index('dates')],
            'index': index_multi[algo]
        }
        index_multi[algo] += 1

    #Write the combinations to a file
    combinations_file_name = network_style + '_combinations.txt' if network_style != '' else 'combinations.txt'
    combinations_file_name = os.path.join('data','fixed_line','gtfs',combinations_file_name)
    with open(combinations_file_name, 'w') as f:
        for combination_name, combination in combinations.items():
            f.write('{}: {}\n'.format(combination_name, combination))
        f.close()
    print("Combinations written to 'combinations.txt' file")

    #Write the multi line combinations to a file
    combinations_multi_file_name = network_style + '_combinations_multi.txt' if network_style != '' else 'combinations_multi.txt'
    combinations_multi_file_name = os.path.join('data','fixed_line','gtfs', combinations_multi_file_name)
    with open(combinations_multi_file_name, 'w') as f:
        for combination_name, combination in combinations_multi.items():
            f.write('{}: {}\n'.format(combination_name, combination))
        f.close()
    return combinations_file_name, combinations_multi_file_name

def read_combinations_from_file(file_path):
    """
    Reads combinations from the given file and parses them into a dictionary.

    Args:
        file_path (str): Path to the combinations file.

    Returns:
        dict: A dictionary with the combination names as keys and their details as values.
    """
    combinations = {}
    with open(file_path, 'r') as f:
        for line in f:
            # Split the line into combination name and details
            combination_name, combination_details = line.split(': ', 1)
            # Evaluate the details string into a Python dictionary
            combinations[combination_name] = eval(combination_details.strip())
    return combinations

def create_test_files(combinations, multi = False, clean = True, network_style ='', instance_name = 'LargeInstanceAll'):
    #Read base test file : python\examples\fixed_line\fixed_line_transfer_synchro_testfile.py
    base_test_file_path = os.path.join('python','examples','fixed_line','fixed_line_transfer_synchro_testfile.py')
    with open(base_test_file_path, 'r') as f:
        lines = f.readlines()
    f.close()

    folder_name = 'test_files_multi' if multi else 'test_files'
    folder_name += '_' + network_style if network_style != '' else ''
    test_folder_path = os.path.join('python','examples','fixed_line', folder_name)
    if clean: #test_folder_path dictory is deleted and recreated
        if os.path.exists(test_folder_path):
            for file in os.listdir(test_folder_path):
                file_path = os.path.join(test_folder_path, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                else:
                    for file in os.listdir(file_path):
                        file_path_new = os.path.join(file_path, file)
                        os.remove(file_path_new)
                    os.rmdir(file_path)
            os.rmdir(test_folder_path)
    
    if not os.path.exists(test_folder_path):
        os.makedirs(test_folder_path)
    test_folder_path_D = os.path.join(test_folder_path, 'D')
    if not os.path.exists(test_folder_path_D):
        os.makedirs(test_folder_path_D)
    test_folder_path_PI = os.path.join(test_folder_path, 'PI')
    if not os.path.exists(test_folder_path_PI):
        os.makedirs(test_folder_path_PI)
    test_folder_path_R = os.path.join(test_folder_path, 'R')
    if not os.path.exists(test_folder_path_R):
        os.makedirs(test_folder_path_R)
    test_folder_path_Offline = os.path.join(test_folder_path, 'Offline')
    if not os.path.exists(test_folder_path_Offline):
        os.makedirs(test_folder_path_Offline)
    
    transfer_hubs = [42482, 43343, 41447, 41801] if network_style == 'transfer_hubs' else []

    for combination_name, combination in combinations.items():
        routes_to_optimize_names = combination['routes_to_optimize_names']
        algo = combination['algo']
        sp = combination['sp']
        ss = combination['ss']
        date = combination['date']
        index = combination['index']
        folder = test_folder_path_D if algo == 1 else test_folder_path_PI if algo == 3 else test_folder_path_R if algo == 2 else test_folder_path_Offline
        testfile_path = os.path.join(folder, 'Test_{}.py'.format(index))
        with open(testfile_path, 'w') as f:
            f.write(f"### DO NOT CHANGE THESE LINES: Parameters are auto-filled in stl_gtfs_parameter_parser_and_test_file_generator.py\n")
            f.write(f"### BEGINNING OF PARAMETERS ###\n")
            f.write(f'import os\n')
            f.write(f'import traceback\n')
            f.write(f'gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-"+str({date})+"-{instance_name+network_style}")\n')
            f.write(f"requests_file_path = os.path.join(gtfs_folder_path,'requests.csv')\n")
            f.write(f"output_folder_path = os.path.join('output','fixed_line','gtfs','gtfs2019-11-'+str({date})+'_{instance_name}')\n")
            f.write(f"output_folder_name = 'gtfs2019-11-'+str({date})+'_{instance_name}'+'_{network_style}'\n")
            f.write(f"routes_to_optimize_names = {routes_to_optimize_names}\n")
            f.write(f"algo = {algo}\n")
            f.write(f"sp = {sp}\n")
            f.write(f"ss = {ss}\n")
            f.write(f"is_corridor = {network_style == 'corridor'}\n")
            f.write(f"transfer_hubs = {transfer_hubs}\n")
            f.write(f"### END OF PARAMETERS ###\n")
            for line in lines[15:]:
                f.write(line)
        f.close()

def generate_slurm_script(
    network_style: str,
    array_start: int = 0,
    array_end: int = 12,
    mem_per_cpu: int = 16,
    time: str = "10:00:00",
    partition: str = "optimum",
    output_dir: str = "generated_scripts"
) -> None:
    """
    Generates a SLURM script for a given instance with customizable parameters.

    Parameters:
        network_style (str): Name of the instance for file paths.
        array_start (int): Start index for SLURM job array. Default is 0.
        array_end (int): End index for SLURM job array. Default is 10.
        mem_per_cpu (int): Memory per CPU in GB. Default is 16GB.
        time (str): Time limit in HH:MM:SS format. Default is 10:00:00.
        partition (str): SLURM partition name. Default is "optimum".
        output_dir (str): Directory where the script will be saved. Default is "generated_scripts".
    """
    if network_style in ['all', 'grid', 'transfer_hubs']:
        mem_per_cpu = 32
        time = "71:59:00"
        partition = "optimumlong"
    elif network_style in ['radial', 'corridor']:
        time ="15:00:00"
    
    script_content = f"""#!/bin/bash
#SBATCH --mem-per-cpu={mem_per_cpu}G
#SBATCH --time={time}
#SBATCH --partition={partition}
#SBATCH --cpus-per-task=1
#SBATCH --output=python/examples/fixed_line/test_files_multi_{network_style}/slurm_output_%A_%a.out
#SBATCH --error=python/examples/fixed_line/test_files_multi_{network_style}/slurm_error_%A_%a.err
#SBATCH --array={array_start}-{array_end} # Array between 0 - 12 for maximum of 13 tasks

# Change to the correct working directory
cd /home/kollau/Recherche_Kolcheva/Simulator

# Load Conda and activate the environment
source /home/kollau/.conda/envs/SimulatorKolcheva/bin/activate

# Define the base directory
BASE_DIR="python/examples/fixed_line/test_files_multi_{network_style}"

# Manually define the list of test files
TEST_FILES=(
    "$BASE_DIR/D/Test_0.py" "$BASE_DIR/D/Test_1.py" "$BASE_DIR/D/Test_2.py" "$BASE_DIR/D/Test_3.py"
    "$BASE_DIR/Offline/Test_0.py"
    "$BASE_DIR/PI/Test_0.py" "$BASE_DIR/PI/Test_1.py" "$BASE_DIR/PI/Test_2.py" "$BASE_DIR/PI/Test_3.py"
    "$BASE_DIR/R/Test_0.py" "$BASE_DIR/R/Test_1.py" "$BASE_DIR/R/Test_2.py" "$BASE_DIR/R/Test_3.py"
)

# Select the test file corresponding to this SLURM task
FILE_TO_RUN=${{TEST_FILES[$SLURM_ARRAY_TASK_ID]}}

# Extract the subfolder and file index
SUB_DIR=$(dirname "$FILE_TO_RUN")
FILE_INDEX=$(basename "$FILE_TO_RUN" | sed 's/Test_\\([0-9]*\\)\\.py/\\1/')

# Print debug information
echo "Running file: $FILE_TO_RUN"
echo "SLURM Task ID: $SLURM_ARRAY_TASK_ID"

# Run the test file and save output/error logs in its corresponding folder
python "$FILE_TO_RUN" > "$SUB_DIR/output_${{FILE_INDEX}}.out" 2> "$SUB_DIR/error_${{FILE_INDEX}}.err"

# Deactivate the Conda environment
conda deactivate
#end of file
"""
    # Output directory 
    output_dir = os.path.join('python','examples','fixed_line','slurm_scripts')

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define output file path
    script_filename = os.path.join(output_dir, f"run_{network_style}.sh")

    # Write script to file
    with open(script_filename, "w") as f:
        f.write(script_content)

    print(f"SLURM script generated: {script_filename}")

### Main code
if __name__ == '__main__':
    for network_style in get_route_dictionary().keys():
        # generate_slurm_script(network_style)
        combinations_file_name, combinations_multi_file_name = parse_parameters_for_transfer_synchro(network_style=network_style)
        # combinations_single = read_combinations_from_file(combinations_file_name)
        combinations_multi = read_combinations_from_file(combinations_multi_file_name)
        instance_name = 'EveningRushHour'
        # create_test_files(combinations_single, multi = False, instance_name=instance_name, network_style = network_style)
        create_test_files(combinations_multi, multi = True, instance_name=instance_name, network_style = network_style)