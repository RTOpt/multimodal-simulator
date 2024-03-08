import logging

logger = logging.getLogger(__name__)


class TravelTimes:

    def __init__(self):
        pass

    def get_expected_arrival_time(self, from_stop, to_stop, vehicle):
        raise NotImplementedError('get_expected_arrival_time not implemented')


class MatrixTravelTimes(TravelTimes):

    def __init__(self, times_matrix):
        super().__init__()
        self.__times_matrix = times_matrix

    def get_expected_arrival_time(self, from_stop, to_stop, vehicle):

        travel_time = \
            self.__times_matrix[vehicle.id][from_stop.location.label][
                to_stop.location.label]
        arrival_time = from_stop.departure_time + travel_time

        return arrival_time
