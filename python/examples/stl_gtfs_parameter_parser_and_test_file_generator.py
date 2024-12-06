import sys
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
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

    combinations = {}
    combinations_multi = {}
    for case in Case:
        params = {
                'lign':Case[case]['ligns'],
                'dir':Case[case]['dirs'],
                "algo": [1, 2, 3],
                "sp": [True, False],
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
        combinations_start_idx = len(combinations)
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
            combination_name = 'combination_{}'.format(i + combinations_start_idx)
            gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-"+str(other_combination[keys.index('dates')])+"-LargeInstance")
            requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
            output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-"+str(other_combination[keys.index('dates')])+"_LargeInstance")
            output_folder_name = "gtfs2019-11-"+str(other_combination[keys.index('dates')])+"_LargeInstance"
            combinations[combination_name] = {
                'routes_to_optimize_names': routes_to_optimize_name,
                'algo': other_combination[keys.index('algo')],
                'sp': other_combination[keys.index('sp')],
                'ss': other_combination[keys.index('ss')],
                'gtfs_folder_path': gtfs_folder_path,
                'requests_file_path': requests_file_path,
                'output_folder_path': output_folder_path,
                'output_folder_name': output_folder_name,
                'date': other_combination[keys.index('dates')]
            }
        
        # Multi line combinations
        routes_to_optimize_names = all_lines_indiv
        combinations_start_idx = len(combinations_multi)
        for i, other_combination in enumerate(other_combinations):
            combination_name = 'combination_{}'.format(i + combinations_start_idx)
            gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-"+str(other_combination[keys.index('dates')])+"-LargeInstance")
            requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
            output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-"+str(other_combination[keys.index('dates')])+"_LargeInstance")
            output_folder_name = "gtfs2019-11-"+str(other_combination[keys.index('dates')])+"_LargeInstance"
            combinations_multi[combination_name] = {
                'routes_to_optimize_names': routes_to_optimize_names,
                'algo': other_combination[keys.index('algo')],
                'sp': other_combination[keys.index('sp')],
                'ss': other_combination[keys.index('ss')],
                'gtfs_folder_path': gtfs_folder_path,
                'requests_file_path': requests_file_path,
                'output_folder_path': output_folder_path,
                'output_folder_name': output_folder_name,
                'date': other_combination[keys.index('dates')]
            }

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

def create_test_files(combinations, multi = False):
    for combination_name, combination in combinations.items():
        gtfs_folder_path = combination['gtfs_folder_path']
        requests_file_path = combination['requests_file_path']
        output_folder_path = combination['output_folder_path']
        output_folder_name = combination['output_folder_name']
        routes_to_optimize_names = combination['routes_to_optimize_names']
        algo = combination['algo']
        sp = combination['sp']
        ss = combination['ss']
        date = combination['date']
        
    
### Main code
combinations_file_name, combinations_multi_file_name = parse_parameters_for_transfer_synchro()
combinations_single = read_combinations_from_file(combinations_file_name)
combinations_multi = read_combinations_from_file(combinations_multi_file_name)
