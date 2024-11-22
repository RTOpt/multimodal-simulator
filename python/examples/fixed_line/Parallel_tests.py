import sys
import os
import logging
import winsound
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
from stl_gtfs_simulator import stl_gtfs_simulator

def run_simulation(gtfs_folder_path, requests_file_path, coordinates_file_path,
                   routes_to_optimize_names, algo, sp, ss, freeze_interval, 
                   output_folder_name, logger, logging_level):
    try:
        stl_gtfs_simulator(
            gtfs_folder_path=gtfs_folder_path,
            requests_file_path=requests_file_path,
            coordinates_file_path=coordinates_file_path,
            routes_to_optimize_names=routes_to_optimize_names,
            ss=ss,  # Allow the use of skip-stop tactics
            sp=sp,  # Allow the use of speedup tactics
            algo=algo,  # 0: offline, 1: deterministic, 2: regret
            freeze_interval=freeze_interval,
            output_folder_name=output_folder_name,
            logger=logger,
            logging_level=logging_level,
            is_from_smartcard_data=True
        )
        return f"Simulation successful for: algo={algo}, ss={ss}, sp={sp}, routes={routes_to_optimize_names}"
    except Exception as e:
        ### Make a beep
        duration = 1000
        freq = 440
        winsound.Beep(freq, duration)
        error_msg = (f"Error in running the simulator with the following parameters: "
                     f"algo: {algo}, ss: {ss}, sp: {sp}, routes: {routes_to_optimize_names}. "
                     f"Error: {e}")
        print(error_msg)
        return error_msg

if __name__ == '__main__':
    # Common settings
    logging_level = logging.INFO
    logger = logging.getLogger(__name__)

    gtfs_folder_path = os.path.join("data", "fixed_line", "gtfs", "gtfs2019-11-01-TestInstanceDurationShort")
    requests_file_path = os.path.join(gtfs_folder_path, "requests.csv")
    output_folder_path = os.path.join("output", "fixed_line", "gtfs", "gtfs2019-11-01-TestInstanceDurationShort")
    output_folder_name = "gtfs2019-11-01_TestInstanceDurationShort"
    coordinates_file_path = None
    freeze_interval = 1

    # Parameters for tests
    route_combinations = [['42E'], ['17N', '151N', '26O', '42E', '56O']]
    algo_values = [2, 3]
    sp_values = [False, True]
    ss_values = [False, True]

    # Prepare tasks for parallel execution
    tasks = []
    with ThreadPoolExecutor() as executor:
        for routes_to_optimize_names in route_combinations:
            for algo in algo_values:
                for sp in sp_values:
                    for ss in ss_values:
                        if algo == 0 and (ss or sp):
                            continue
                        tasks.append(executor.submit(
                            run_simulation,
                            gtfs_folder_path,
                            requests_file_path,
                            coordinates_file_path,
                            routes_to_optimize_names,
                            algo,
                            sp,
                            ss,
                            freeze_interval,
                            output_folder_name,
                            logger,
                            logging_level
                        ))
        
        # Collect results as tasks complete
        for future in as_completed(tasks):
            print(future.result())
