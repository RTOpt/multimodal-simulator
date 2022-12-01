import logging

from multimodalsim.reader.gtfs_generator import GTFSGenerator

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    passage_arret_folder = \
        "../../../../donnees_de_mobilite/Donnees_STL_3_jours/" \
        "Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30/"
    gtfs_folder = "../../data/fixed_line/stl/gtfs_test/"

    gtfs_generator = GTFSGenerator(gtfs_folder)

    for i in range(0, 4):
        logger.info(i)
        passage_arret_file_name = \
            "Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30_" + str(i) \
            + ".csv"
        save_path = "output/"
        gtfs_generator.build_trips(passage_arret_file_name,
            passage_arret_folder)
        gtfs_generator.build_stop_times(passage_arret_file_name,
                                        passage_arret_folder)
