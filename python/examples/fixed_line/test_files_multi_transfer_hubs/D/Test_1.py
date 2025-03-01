### DO NOT CHANGE THESE LINES: Parameters are auto-filled in stl_gtfs_parameter_parser_and_test_file_generator.py
### BEGINNING OF PARAMETERS ###
import os
import traceback
gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-"+str(25)+"-EveningRushHourtransfer_hubs")
requests_file_path = os.path.join(gtfs_folder_path,'requests.csv')
output_folder_path = os.path.join('output','fixed_line','gtfs','gtfs2019-11-'+str(25)+'_EveningRushHour')
output_folder_name = 'gtfs2019-11-'+str(25)+'_EveningRushHour'+'_transfer_hubs'
routes_to_optimize_names = ['144E', '144O', '151N', '151S', '17N', '17S', '20E', '20O', '222E', '222O', '22E', '22O', '24E', '24O', '252E', '252O', '26E', '26O', '27N', '27S', '33N', '33S', '37N', '37S', '41N', '41S', '42E', '42O', '43N', '43S', '45N', '45S', '46N', '46S', '52E', '52O', '55N', '55S', '56E', '56O', '60E', '60O', '61N', '61S', '63N', '63S', '65N', '65S', '66E', '66O', '70E', '70O', '74E', '74O', '76E', '76O', '901N', '901S', '902N', '902S', '903N', '903S', '925N', '925S', '942E', '942O']
algo = 1
sp = False
ss = True
is_corridor = False
transfer_hubs = [42482, 43343, 41447, 41801]
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
                        is_from_smartcard_data = True,
                        is_corridor = is_corridor,
                        transfer_hubs = transfer_hubs
                        )
    final_time = time.time() - start_time
    print('Execution time: ', final_time)
    print('End testing...')
except Exception as e:
    print('An error occured during the simulation')
    # traceback.print_exc()
    error_traceback = traceback.format_exc()
    print('Error traceback: ', error_traceback)
    final_time = time.time() - start_time
    print('Execution time: ', final_time)
    print('End testing after error...')