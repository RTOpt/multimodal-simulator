### Parameters are auto-filled in stl_gtfs_parameter_parser_and_test_file_generator.py
gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-25-TestInstanceDurationCASPT_NEW")
requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-25_TestInstanceDurationCASPT_NEW")
output_folder_name = "gtfs2019-11-25_TestInstanceDurationCASPT_NEW"
routes_to_optimize_names = [['17N'], ['151S'], ['26E'], ['42E'], ['56E']]
algo = 0
sp = False
ss = True
### END OF PARAMETERS ###

import sys
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
from stl_gtfs_transfer_synchro_simulator import*
import datetime
import traceback

logging_level = logging.WARNING
logger = logging.getLogger(__name__)
coordinates_file_path = None
freeze_interval = 1

#Create error file and create it if it does not exist with timestamp
error_file_path = os.path.join(output_folder_path, "error.txt")
if not os.path.exists(output_folder_path):
    os.makedirs(output_folder_path)
if not os.path.exists(error_file_path):
    with open(error_file_path, "w") as f:
        f.write("Error file path created at {}\n".format(datetime.datetime.now()))
    f.close()
else:
    with open(error_file_path, "a") as f:
        f.write("Error file path created at {}\n".format(datetime.datetime.now()))
    f.close()

try:
    stl_gtfs_transfer_synchro_simulator(
                        gtfs_folder_path=gtfs_folder_path,
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
    error_message = "Error in running the simulator with the following parameters: algo: {}, ss: {}, sp: {}, routes: {}\n".format(algo, ss, sp, routes_to_optimize_names)
    error_traceback = traceback.format_exc()  # Get full traceback

    # Append error details to the log file
    with open(error_file_path, "a") as f:
        f.write(error_message)
        f.write('Error message: {}\n'.format(e))
        f.write("Traceback:\n")
        f.write(error_traceback)

# Offline
routes_to_optimize_names = [ '17N', '151S', '26E', '42E', '56E']
stl_gtfs_transfer_synchro_simulator(gtfs_folder_path = gtfs_folder_path,
                    requests_file_path = requests_file_path,
                    coordinates_file_path = coordinates_file_path,
                    routes_to_optimize_names = routes_to_optimize_names,
                    ss = False, # Allow the use of skip-stop tactics
                    sp = False, # Allow the use of speedup tactics
                    algo = 0, # 0: offline, 1: deterministic, 2: regret, 3: Perfect Information
                    freeze_interval = freeze_interval,
                    output_folder_name = output_folder_name,
                    logger = logger,
                    logging_level = logging_level,
                    is_from_smartcard_data = True
                    )
