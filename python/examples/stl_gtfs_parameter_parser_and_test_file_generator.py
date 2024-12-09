import sys
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
sys.path.append(r"/home/kollau/Recherche_Kolcheva/multimodal-simulator/python/examples")
from itertools import product
import os

def parse_parameters_for_transfer_synchro():
    all_ligns_SN= ['151', '17', '27', '33', '37', '41', '43', '45', '46', '55', '61', '63', '65', '901', '902', '903', '925']
    all_ligns_EO= ['144', '20', '222', '22', '24','252', '26', '2', '36', '52', '56', '60', '66', '74', '76', '942']
    Case={}
    Case['EO']={}
    Case['EO']['ligns']=all_ligns_EO
    Case['EO']['dirs']=['E','O']
    Case['EO']['dirs']=['E']
    Case['SN']={}
    Case['SN']['ligns']=all_ligns_SN
    Case['SN']['dirs']=['S','N']

    index = {}
    for i in range(4):
        index[i] = 0
    index_multi = {}
    for i in range(4):
        index_multi[i] = 0
    combinations = {}
    combinations_multi = {}
    for case in Case:
        params = {
                "algo": [0, 1, 2, 3],
                'lign':Case[case]['ligns'],
                'dir':Case[case]['dirs'],
                "sp": [False, True],
                "ss": [False, True],
                'dates': [25, 26, 27]
            }
        keys = list(params.keys())
        values = list(params.values())

        # Separate 'lign' and 'dir' values
        lign_values = values[keys.index('lign')]
        dir_values = values[keys.index('dir')]

        # Remove 'lign' and 'dir' from keys and values
        keys.remove('lign')
        keys.remove('dir')
        values.remove(lign_values)
        values.remove(dir_values)
        # Create combinations of 'lign' and 'dir'
        all_lines_indiv = list(product(lign_values, dir_values))
        all_lines_indiv = [line[0]+line[1] for line in all_lines_indiv]
        #Create a list with : all individual lines
        routes_to_optimize_names=[]
        for line in all_lines_indiv:
            routes_to_optimize_names.append([line,])
        # routes_to_optimize_names.append(all_lines_indiv)
        print(routes_to_optimize_names)
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
    combinations_file_name = os.path.join('data','fixed_line','gtfs','combinations.txt')
    with open(combinations_file_name, 'w') as f:
        for combination_name, combination in combinations.items():
            f.write('{}: {}\n'.format(combination_name, combination))
        f.close()
    print("Combinations written to 'combinations.txt' file")

    #Write the multi line combinations to a file
    combinations_multi_file_name = os.path.join('data','fixed_line','gtfs','combinations_multi.txt')
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

def create_test_files(combinations, multi = False, clean = True):
    #Read base test file : python\examples\fixed_line\fixed_line_transfer_synchro_testfile.py
    base_test_file_path = os.path.join('python','examples','fixed_line','fixed_line_transfer_synchro_testfile.py')
    with open(base_test_file_path, 'r') as f:
        lines = f.readlines()
    f.close()

    folder_name = 'test_files_multi' if multi else 'test_files'
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
            f.write(f'gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-"+str({date})+"-LargeInstance")\n')
            f.write(f"requests_file_path = os.path.join(gtfs_folder_path,'requests.csv')\n")
            f.write(f"output_folder_path = os.path.join('output','fixed_line','gtfs','gtfs2019-11-'+str({date})+'_LargeInstance')\n")
            f.write(f"output_folder_name = 'gtfs2019-11-'+str({date})+'_LargeInstance'\n")
            f.write(f"routes_to_optimize_names = {routes_to_optimize_names}\n")
            f.write(f"algo = {algo}\n")
            f.write(f"sp = {sp}\n")
            f.write(f"ss = {ss}\n")
            f.write(f"### END OF PARAMETERS ###\n")
            for line in lines[12:]:
                f.write(line)
        f.close()
    
### Main code
combinations_file_name, combinations_multi_file_name = parse_parameters_for_transfer_synchro()
combinations_single = read_combinations_from_file(combinations_file_name)
combinations_multi = read_combinations_from_file(combinations_multi_file_name)
create_test_files(combinations_single)
create_test_files(combinations_multi, multi = True)