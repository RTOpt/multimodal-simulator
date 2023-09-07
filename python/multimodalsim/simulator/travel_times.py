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
        # logger.warning("{}: {} -> {}".format(vehicle.id, str(from_stop.location), str(to_stop.location)))
        # logger.warning("{}: {} -> {}".format(type(vehicle.id), type(from_stop.location),
        #                                      type(to_stop.location)))
        # logger.warning(self.__times_matrix[vehicle.id])
        # logger.warning(self.__times_matrix[vehicle.id][str(from_stop.location)])
        # logger.warning(self.__times_matrix[vehicle.id][str(from_stop.location)][str(to_stop.location)])

        travel_time = \
            self.__times_matrix[vehicle.id][str(from_stop.location)][
                str(to_stop.location)]
        arrival_time = from_stop.departure_time + travel_time

        return arrival_time
