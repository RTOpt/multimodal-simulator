import sys
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
from stl_gtfs_simulator import*
import winsound

## This file runs the Multimodal Simulator for the whole month of November 2019 day by day with real STL Data.
if __name__ == '__main__':
    small = False
    # the log level (at INFO, by default)
    logging_level = logging.WARNING
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
    

    # Test for all lines in the bus network over a shorter period.
    gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-01-TestInstanceDurationShort")
    requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
    output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-01-TestInstanceDurationShort")
    output_folder_name = "gtfs2019-11-01_TestInstanceDurationShort"
    coordinates_file_path = None
    freeze_interval = 1
    routes_to_optimize_names = [ '17S', '151N', '26O', '42E'] # grid style network
    routes_to_optimize_names = ['42O']
# Offline
# stl_gtfs_simulator(gtfs_folder_path = gtfs_folder_path,
#                     requests_file_path = requests_file_path,
#                     coordinates_file_path = coordinates_file_path,
#                     routes_to_optimize_names = routes_to_optimize_names,
#                     ss = False, # Allow the use of skip-stop tactics
#                     sp = False, # Allow the use of speedup tactics
#                     algo = 0, # 0: offline, 1: deterministic, 2: regret, 3: Perfect Information
#                     freeze_interval = freeze_interval,
#                     output_folder_name = output_folder_name,
#                     logger = logger,
#                     logging_level = logging_level,
#                     is_from_smartcard_data = True
#                     )
# # # Intelligent splitter 
# stl_gtfs_simulator(gtfs_folder_path = gtfs_folder_path,
#                     requests_file_path = requests_file_path,
#                     coordinates_file_path = coordinates_file_path,
#                     routes_to_optimize_names = routes_to_optimize_names,
#                     ss = False, # Allow the use of skip-stop tactics
#                     sp = False, # Allow the use of speedup tactics
#                     algo = 0, # 0: offline, 1: deterministic, 2: regret, 3: Perfect Information
#                     freeze_interval = freeze_interval,
#                     output_folder_name = output_folder_name,
#                     logger = logger,
#                     logging_level = logging_level,
#                     is_from_smartcard_data = False
#                     )
# All other combinations
for routes_to_optimize_names in [['42E'],[ '17N', '151N', '26O', '42E', '56O']]:
# for routes_to_optimize_names in [['70E'], ['70E', '31S', '37S', '39S', '33S']]:
    for algo in [2, 3]:
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
                    ### Make a beep
                    duration = 1000
                    freq = 440
                    winsound.Beep(freq, duration)
                    print("Error in running the simulator with the following parameters: algo: {}, ss: {}, sp: {}, routes: {}".format(algo, ss, sp, routes_to_optimize_names))
