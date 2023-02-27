import logging

from multimodalsim.reader.gtfs_generator import GTFSGenerator

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    passage_arret_folder = \
        "../../../../donnees_de_mobilite/data/stl/Donnees_STL_3_jours/"
    gtfs_folder = "../../data/fixed_line/stl/gtfs_2023_02_17/"

    passage_arret_folder = \
        passage_arret_folder \
        + "Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30/mod/"
    passage_arret_file_path_list = [
        passage_arret_folder
        + "Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30_0.csv",
        passage_arret_folder
        + "Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30_1_mod.csv",
        passage_arret_folder
        + "Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30_2_mod.csv",
        passage_arret_folder
        + "Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30_3_mod.csv"]

    gtfs_generator = GTFSGenerator()

    logger.info("build_calendar_dates")
    gtfs_generator.build_calendar_dates(passage_arret_file_path_list,
                                        gtfs_folder)
    logger.info("done")

    logger.info("build_trips")
    gtfs_generator.build_trips(passage_arret_file_path_list, gtfs_folder)
    logger.info("done")

    logger.info("build_stops")
    gtfs_generator.build_stops(passage_arret_file_path_list, gtfs_folder)
    logger.info("done")

    logger.info("build_stop_times")
    gtfs_generator.build_stop_times(passage_arret_file_path_list, gtfs_folder,
                                    shape_dist_traveled=True)
    logger.info("done")

