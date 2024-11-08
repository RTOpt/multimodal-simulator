import sys
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
from stl_gtfs_simulator import*

# Redirect stdout and stderr to the logger
class StreamToLogger:
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

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
        routes_to_optimize_names = ['70E'] #radial style network
    
    gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs2019-11-01-TestInstance")
    requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
    output_folder_path = os.path.join("output","fixed_line","gtfs","gtfs2019-11-01-TestInstance")
    output_folder_name = "gtfs2019-11-01-TestInstance"
    coordinates_file_path = None
    freeze_interval = 1
    # routes_to_optimize_names = ['70E', '31S', '37S', '39S', '33S'] #radial style network
    routes_to_optimize_names = []

    ### routes_to_optimize_names = ['24E', '17S', '151S', '56E', '42E'] # grid style network

    # #Set up logging and error file
    # error_file = os.path.join(output_folder_path,"error.log")
    # logger_file = os.path.join(output_folder_path,"simulation.log")
    # # Set up file handler to write to logger_file (simulation.log)
    # file_handler = logging.FileHandler(logger_file, mode = 'w')
    # file_handler.setLevel(logging.WARNING)
    # # Define logging format
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # file_handler.setFormatter(formatter)
    # # Add file handler to logger
    # logger.addHandler(file_handler)

    # Redirect standard output and error to the logger
    # sys.stdout = StreamToLogger(logger, logging.INFO)
    # sys.stderr = StreamToLogger(logger, logging.ERROR)

    # for ss in [False, True]:
    #     for sp in [False, True]:
    #         for algo in [0, 1, 2]:
    #             algo_name = ["offline", "deterministic", "regret"][algo]
    #             try:
    #                 logger.info(f"Running simulation with ss={ss}, sp={sp}, algo={algo_name}")
stl_gtfs_simulator(gtfs_folder_path=gtfs_folder_path,
                requests_file_path=requests_file_path,
                coordinates_file_path=coordinates_file_path,
                routes_to_optimize_names = routes_to_optimize_names,
                ss = False, # Allow the use of skip-stop tactics
                sp = False, # Allow the use of speedup tactics
                algo = 0, # 0: offline, 1: deterministic, 2: regret
                freeze_interval = freeze_interval,
                output_folder_name = output_folder_name,
                logger = logger,
                logging_level = logging_level,
                )
                # except Exception as e:
                #     # Log the error to the logger and the error log file
                #     logger.error(f"Error encountered with ss = {ss}, sp = {sp}, algo = {algo_name}: {e}")
                #     with open(error_file, "a") as f:
                #         f.write(f"ss={ss}, sp={sp}, algo={algo_name}, error={e}\n")
                #     f.close()
                #     input()
                    
    # # Restore stdout and stderr
    # sys.stdout = sys.__stdout__
    # sys.stderr = sys.__stderr__