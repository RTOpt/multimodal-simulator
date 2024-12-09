### DO NOT CHANGE THESE LINES: Parameters are auto-filled in stl_gtfs_parameter_parser_and_test_file_generator.py
### BEGINNING OF PARAMETERS ###
import os
gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-25-TestInstanceDurationCASPT_NEW")
requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-25_TestInstanceDurationCASPT_NEW")
output_folder_name = "gtfs2019-11-25_TestInstanceDurationCASPT_NEW"
routes_to_optimize_names = ['17N', '151S', '26E', '42E','56E']
algo = 0
sp = False
ss = False
### END OF PARAMETERS ###

import sys
import time
import logging
sys.path.append(os.path.abspath('../../..'))
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
sys.path.append(r"/home/kollau/Recherche_Kolcheva/multimodal-simulator/python/examples")
from examples.stl_gtfs_transfer_synchro import stl_gtfs_transfer_synchro_simulator
logging_level = logging.WARNING
logger = logging.getLogger(__name__)
start_time=time.time()
print('Begin testing...')
coordinates_file_path = None
freeze_interval = 1
stl_gtfs_transfer_synchro_simulator(
                    gtfs_folder_path=gtfs_folder_path,
                    requests_file_path=requests_file_path,
                    coordinates_file_path=coordinates_file_path,
                    routes_to_optimize_names = routes_to_optimize_names,
                    ss = ss, # Allow the use of skip-stop tactics
                    sp = sp, # Allow the use of speedup tactics
                    algo = algo, # 0: offline, 1: deterministic, 2: regret, 3: Perfect Information
                    freeze_interval = freeze_interval,
                    output_folder_name = output_folder_name,
                    logger = logger,
                    logging_level = logging_level,
                    is_from_smartcard_data = True
                    )
final_time = time.time() - start_time
print('Execution time: ', final_time)
print('End testing...')