from gtfs_generator import GTFSGenerator
import os

#Source file
path=r"D:\donnees\Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30.csv"
passage_arret_file_path_list=[path]
#Destination folder
gtfs_folder=os.path.join("data","fixed_line","gtfs","gtfs")

#Generate GTFS files
gtfs_generator = GTFSGenerator()
gtfs_generator.build_calendar_dates(passage_arret_file_path_list=passage_arret_file_path_list, gtfs_folder=gtfs_folder)
gtfs_generator.build_trips(passage_arret_file_path_list=passage_arret_file_path_list, gtfs_folder=gtfs_folder)
gtfs_generator.build_stops(passage_arret_file_path_list=passage_arret_file_path_list, gtfs_folder=gtfs_folder)
gtfs_generator.build_stop_times(passage_arret_file_path_list=passage_arret_file_path_list, gtfs_folder=gtfs_folder)
