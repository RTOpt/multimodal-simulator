### DO NOT CHANGE THESE LINES: Parameters are auto-filled in stl_gtfs_parameter_parser_and_test_file_generator.py
### BEGINNING OF PARAMETERS ###
import os
import traceback
gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-25-LargeInstanceAll")
requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-25_LargeInstanceAll")
output_folder_name = "gtfs2019-11-25_LargeInstanceAll"
routes_to_optimize_names =  ['144E', '144O', '20E', '20O', '222E', '222O', '22E', '22O', '24E', '24O', '252E', '252O', '26E', '26O', '42E', '42O', '52E', '52O', '56E', '56O', '60E', '60O', '66E', '66O', '70E', '70O', '74E', '74O', '76E', '76O', '942E', '942O', '151S', '151N', '17S', '17N', '27S', '27N', '33S', '33N', '37S', '37N', '41S', '41N', '43S', '43N', '45S', '45N', '46S', '46N', '55S', '55N', '61S', '61N', '63S', '63N', '65S', '65N', '901S', '901N', '902S', '902N', '903S', '903N', '925S', '925N']
algo = 0
sp = False
ss = False
### END OF PARAMETERS ###

import sys
import time
import logging
sys.path.append(os.path.abspath('../../..'))
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
sys.path.append(r"/home/kollau/Recherche_Kolcheva/Simulator/python/examples")
from stl_gtfs_transfer_synchro import stl_gtfs_transfer_synchro_simulator
# Setup the logger
logging_level = logging.WARNING
logger = logging.getLogger(__name__)
# Start the simulation
start_time=time.time()
print('Begin testing...')
coordinates_file_path = None
freeze_interval = 1
try: 
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
except Exception as e:
    print('An error occured during the simulation')
    traceback.print_exc()
    final_time = time.time() - start_time
    print('Execution time: ', final_time)
    print('End testing after error...')