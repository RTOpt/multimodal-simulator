import logging

from multimodalsim.simulator.stop import Stop
from multimodalsim.simulator.vehicle import Vehicle

logger = logging.getLogger(__name__)


class TravelTimes:

    def __init__(self):
        pass

    def get_expected_arrival_time(self, from_stop: Stop, to_stop: Stop,
                                  vehicle: Vehicle) -> int:
        raise NotImplementedError('get_expected_arrival_time not implemented')


class MatrixTravelTimes(TravelTimes):

    def __init__(self, times_matrix: dict[str | int, dict[str | int, int]]):
        super().__init__()
        self.__times_matrix = times_matrix

    def get_expected_arrival_time(self, from_stop: Stop, to_stop: Stop,
                                  vehicle: Vehicle) -> int:

        travel_time = \
            self.__times_matrix[vehicle.id][from_stop.location.label][
                to_stop.location.label]
        arrival_time = from_stop.departure_time + travel_time

        return arrival_time
