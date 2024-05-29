# This file runs the Multimodal Simulator for the whole month of November 2019 day by day with real STL Data.
import sys
sys.path.append(r"C:\Users\kklau\Desktop\Simulator\python\examples")
from stl_gtfs_simulator import*

logger = logging.getLogger(__name__)

## This file runs the Multimodal Simulator for the whole month of November 2019 day by day with real STL Data.
if __name__ == '__main__':
    # To modify the log level (at INFO, by default)
    loggin_level=logging.INFO
    for dateshort in ["20191101","20191102","20191103","20191104","20191105","20191106","20191107","20191108","20191109","20191110","20191111","20191112","20191113","20191114","20191115","20191116","20191117","20191118","20191119","20191120","20191121","20191122","20191123","20191124","20191125","20191126","20191127","20191128","20191129","20191130"]:
        logger.info(" Start simulation of date: "+dateshort)
        date=dateshort[0:4]+"-"+dateshort[4:6]+"-"+dateshort[6:8]

        # Read input data from files with a DataReader. The DataReader returns a
        # list of Vehicle objects and a list of Trip objects.
        gtfs_folder_path = os.path.join("data","fixed_line","gtfs","gtfs"+date)
        requests_file_path = os.path.join("data","fixed_line","gtfs","gtfs"+date,"requests.csv")
        coordinates_file_path = None
        freeze_interval = 20
        stl_gtfs_simulator(gtfs_folder_path=gtfs_folder_path,
                           requests_file_path=requests_file_path,
                           coordinates_file_path=coordinates_file_path,
                           freeze_interval=freeze_interval,
                           logger=logger,
                           loggin_level=loggin_level)