import sys
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
from stl_gtfs_simulator import*

## This file runs the Multimodal Simulator for the whole month of November 2019 day by day with real STL Data.
if __name__ == '__main__':
    small = False
    # the log level (at INFO, by default)
    logging_level = logging.INFO
    logger = logging.getLogger(__name__)
    # logging.captureWarnings(True)
    if small:
        gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs-generated-small")
        requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
        output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs-generated-small")
        output_folder_name = "gtfs-generated-small"
        coordinates_file_path = None
        freeze_interval = 1
        routes_to_optimize_names = ['70E']
    else:
        gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs-generated")
        requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
        output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs-generated")
        output_folder_name = "gtfs-generated"
        coordinates_file_path = None
        freeze_interval = 1
        routes_to_optimize_names = ['70E']
    
    ### Test for lines ['70E', '31S', '37S', '39S', '33S'] with 3 bus trips each.
    # gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-01-TestInstance")
    # requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
    # output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-01-TestInstance")
    # output_folder_name = "gtfs2019-11-01-TestInstance"
    # coordinates_file_path = None
    # freeze_interval = 1
    # routes_to_optimize_names = ['70E', '31S', '37S', '39S', '33S'] #radial style network

    ### Test for all lines in the bus network over a period of 1 hour.
    gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-01-TestInstanceDuration")
    requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
    output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-01-TestInstanceDuration")
    output_folder_name = "gtfs2019-11-01_TestInstanceDuration"
    coordinates_file_path = None
    freeze_interval = 1

    # routes_to_optimize_names = ['70E', '31S', '37S', '39S', '33S'] # radial style network
    # routes_to_optimize_names = ['24E', '17S', '151S', '56E', '42E'] # grid style network

    routes_to_optimize_names = ['42O']
# Offline
stl_gtfs_simulator(gtfs_folder_path = gtfs_folder_path,
                    requests_file_path = requests_file_path,
                    coordinates_file_path = coordinates_file_path,
                    routes_to_optimize_names = routes_to_optimize_names,
                    ss = False, # Allow the use of skip-stop tactics
                    sp = False, # Allow the use of speedup tactics
                    algo = 0, # 0: offline, 1: deterministic, 2: regret
                    freeze_interval = freeze_interval,
                    output_folder_name = output_folder_name,
                    logger = logger,
                    logging_level = logging_level,
                    is_from_smartcard_data = True
                    )
# Intelligent splitter 
stl_gtfs_simulator(gtfs_folder_path = gtfs_folder_path,
                    requests_file_path = requests_file_path,
                    coordinates_file_path = coordinates_file_path,
                    routes_to_optimize_names = routes_to_optimize_names,
                    ss = False, # Allow the use of skip-stop tactics
                    sp = False, # Allow the use of speedup tactics
                    algo = 0, # 0: offline, 1: deterministic, 2: regret
                    freeze_interval = freeze_interval,
                    output_folder_name = output_folder_name,
                    logger = logger,
                    logging_level = logging_level,
                    is_from_smartcard_data = False
                    )
# All other combinations
for routes_to_optimize_names in [['42E'], ['24E', '17S', '151S', '56E', '42E']]:
    for algo in [1, 2, 3]:
        for sp in [False, True]:
            for ss in [False, True]:
                if algo == 0 and (ss or sp):
                    continue
                try:
                    stl_gtfs_simulator(gtfs_folder_path=gtfs_folder_path,
                                    requests_file_path=requests_file_path,
                                    coordinates_file_path=coordinates_file_path,
                                    routes_to_optimize_names = routes_to_optimize_names,
                                    ss = ss, # Allow the use of skip-stop tactics
                                    sp = sp, # Allow the use of speedup tactics
                                    algo = algo, # 0: offline, 1: deterministic, 2: regret
                                    freeze_interval = freeze_interval,
                                    output_folder_name = output_folder_name,
                                    logger = logger,
                                    logging_level = logging_level,
                                    is_from_smartcard_data = True
                                    )
                except Exception as e:
                    print(e)
                    print(f"ss={ss}, sp={sp}, algo ={algo}")