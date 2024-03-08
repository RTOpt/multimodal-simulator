import csv
import logging

from multimodalsim.simulator.travel_times import MatrixTravelTimes

logger = logging.getLogger(__name__)


class MatrixTravelTimesReader:

    def __init__(self, travel_times_file_path):
        self.__travel_times_file_path = travel_times_file_path

    def get_matrix_travel_times(self):

        times_matrix = self.__read_from_file()

        matrix_travel_times = MatrixTravelTimes(times_matrix)

        return matrix_travel_times

    def __read_from_file(self):

        times_matrix = {}

        with open(self.__travel_times_file_path, 'r') as travel_times_file:
            travel_times_reader = csv.reader(travel_times_file, delimiter=',')
            next(travel_times_reader, None)
            for row in travel_times_reader:
                vehicle_id = row[0]
                from_stop = row[1]
                to_stop = row[2]
                travel_time = int(row[3])

                if vehicle_id not in times_matrix:
                    times_matrix[vehicle_id] = {}

                if from_stop not in times_matrix[vehicle_id]:
                    times_matrix[vehicle_id][from_stop] = {}

                times_matrix[vehicle_id][from_stop][to_stop] = travel_time

        return times_matrix
