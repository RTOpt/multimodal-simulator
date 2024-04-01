import sys
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
from stl_gtfs_simulator import*

logger = logging.getLogger(__name__)
small=True
## This file runs the Multimodal Simulator for the whole month of November 2019 day by day with real STL Data.
if __name__ == '__main__':
    # To modify the log level (at INFO, by default)
    loggin_level=logging.INFO
    logger.info(" Start simulation for small instance")
    if small:
        gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs-generated-small")
        requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
        output_folder_path=os.path.join("output","fixed_line","gtfs","gtfs-generated-small")
        coordinates_file_path=None
        freeze_interval=1
    else:
        gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs-generated")
        requests_file_path = os.path.join(gtfs_folder_path,"requests.csv")
        output_folder_path=os.path.join("output","fixed_line","gtfs","gtfs-generated")
        coordinates_file_path=None
        freeze_interval=1
    stl_gtfs_simulator(gtfs_folder_path=gtfs_folder_path,
                       requests_file_path=requests_file_path,
                       coordinates_file_path=coordinates_file_path,
                       freeze_interval=freeze_interval,
                       output_folder_path=output_folder_path,
                       logger=logger,
                       loggin_level=loggin_level,
                       main_line="2790970")