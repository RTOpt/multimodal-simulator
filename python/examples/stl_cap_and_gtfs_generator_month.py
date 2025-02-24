from multimodalsim.reader.gtfs_generator import GTFSGenerator
from multimodalsim.reader.available_connections_extractor import AvailableConnectionsExtractor
from multimodalsim.reader.requests_generator import CAPRequestsGenerator
import logging
import os
import argparse
import pandas as pd

logger = logging.getLogger(__name__)

### This file generates the GTFS files from the STL data for the whole month of November 2019 day by day
### This file also generates the requests and available connections for the whole month of November 2019 day by day
if __name__ == '__main__':
    # Import STL files (personal) : Source file (replace with your own path)
    path = r"D:\donnees\Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30.csv"
    passage_arret_file_path_list = [path]
    # Destination folder
    gtfs_folder = os.path.join("data","fixed_line","gtfs","gtfs")

    #Generate GTFS files (do once)
    gtfs_generator = GTFSGenerator()
    logger.info("build_calendar_dates")
    # gtfs_generator.build_calendar_dates(passage_arret_file_path_list=passage_arret_file_path_list, gtfs_folder=gtfs_folder)
    # logger.info("build_trips")
    # gtfs_generator.build_trips(passage_arret_file_path_list=passage_arret_file_path_list, gtfs_folder=gtfs_folder)
    # logger.info("build_stops")
    # gtfs_generator.build_stops(passage_arret_file_path_list=passage_arret_file_path_list, gtfs_folder=gtfs_folder)
    # logger.info("build_stop_times")
    # gtfs_generator.build_stop_times(passage_arret_file_path_list=passage_arret_file_path_list, gtfs_folder=gtfs_folder, shape_dist_traveled=False)
    # logger.info("build_stop_times_upgrade")
    # gtfs_generator.build_stop_times_upgrade(passage_arret_file_path_list=passage_arret_file_path_list, gtfs_folder=gtfs_folder, shape_dist_traveled=True)
    # logger.info("Done importing GTFS files")

    ## Split large .csv file into daily files (do once and then comment out)
    # logger.info("Split large .csv file into daily files")
    # ## Source file (replace with your own path)
    # passage_arret_df = pd.read_csv(r"D:\donnees\Donnees_CAP_GFI_SPOT_2019-11-01_2019-11-30\Donnees_CAP_GFI_SPOT_2019-11-01_2019-11-30.csv", delimiter = ',')
    # new_cap_folder = os.path.join("D:","donnees","New donnees")
    # dates_list = passage_arret_df['DATE28'].unique()
    # for date in dates_list:
    #     trips_day_df = passage_arret_df[
    #         passage_arret_df['DATE28'] == date].drop('DATE28', axis=1)
    #     cap_filename = date.split(" ")[0].replace("-", "") + ".csv"
    #     trips_day_df.to_csv(os.path.join(new_cap_folder, cap_filename), index = None, sep = ';')
    
    # Extract all lines from GTFS files
    # all_lines_SN, all_lines_EO = gtfs_generator.get_all_lines()

    ##  Extract available connections from CAP Data (do once and then comment out)
    ## If you want to change release_time_delta, ready_time_delta, due_time_delta used in the optimization, you have to regenerate this part.
    logging.getLogger().setLevel(logging.DEBUG)
    dates = ["20191101","20191102","20191103","20191104","20191105","20191106","20191107","20191108","20191109","20191110","20191111","20191112","20191113","20191114","20191115","20191116","20191117","20191118","20191119","20191120","20191121","20191122","20191123","20191124","20191125","20191126","20191127","20191128","20191129","20191130"]
    for dateshort in dates:
        ## Get the date and the paths to all the files
        logger.info("Date: " + dateshort)
        cap_filepath = os.path.join("D:", "donnees", "New donnees", dateshort + ".csv")
        cap_filepath = os.path.join('data', 'fixed_line', 'CAP_month', dateshort + '.csv')
        date = dateshort[0:4]+"-"+dateshort[4:6]+"-"+dateshort[6:8]
        date_folder = os.path.join("data", "fixed_line", "gtfs", "gtfs"+date)
        stop_times_filepath = os.path.join("data", "fixed_line", "gtfs", "gtfs"+date, "stop_times_upgrade.txt")
        trips_filepath = os.path.join("data", "fixed_line", "gtfs","gtfs"+date, "trips.txt")
        requests_savepath = os.path.join("data", "fixed_line", "gtfs", "gtfs"+date, "requests.csv")
        connections_savepath = os.path.join("data", "fixed_line", "gtfs", "gtfs"+date, "available_connections.json")
        logger.info("Fill missing stop times...")

        # Fill missing stop times
        gtfs_generator.fill_missing_stop_times(date_folder)

        ## Parse arguments for the CAPRequestsGenerator
        parser = argparse.ArgumentParser()
        parser.add_argument("--cap", help="path to the file containing CAP "
                                                "data.")
        parser.add_argument("-s", "--stoptimes", help="path to the file containing"
                                                    " the GTFS stop times.")
        parser.add_argument("-r", "--requests", help="path to output file that "
                                                    "will contain the requests.")
        parser.add_argument("-c", "--connections", help="path to output file that "
                                                        "will contain the "
                                                        "available connections.")
        parser.add_argument("-t", "--trips", help="path to the file containing bus trips")
        args = parser.parse_args(["--cap",cap_filepath,"-s",stop_times_filepath,"-r",requests_savepath,"-c",connections_savepath, "-t", trips_filepath])

        # Generate requests for the day
        logger.info("CAPRequestsGenerator for date: "+date)
        stl_cap_requests_generator = CAPRequestsGenerator(args.cap, args.stoptimes, trips_file_path = args.trips)
        requests_df = stl_cap_requests_generator.generate_requests(max_connection_time = 5400,
                                                                   release_time_delta = 300,
                                                                   ready_time_delta = 60,
                                                                   due_time_delta = 3600)

        # Save to file
        stl_cap_requests_generator.save_to_csv(args.requests)

        # # AvailableConnectionsExtractor (do once and then comment out)
        logger.info("AvailableConnectionsExtractor for date: "+date)
        available_connections_extractor = \
            AvailableConnectionsExtractor(args.cap, args.stoptimes)

        max_distance = 0.5
        available_connections = available_connections_extractor.extract_available_connections(max_distance)

        # Save to file
        available_connections_extractor.save_to_json(args.connections)
        logger.info("Done extracting available connections for date: "+date)
    
    ## Get route_stops for the month of November 2019 (do once and then comment out)
    gtfs_generator.create_stops_per_line_month_files()
    gtfs_generator.create_travel_times_month_files()
    gtfs_generator.create_passenger_flow_month_files()
    logger.info("Done extracting available connections for all dates")