import logging
import csv

from multimodalsim.coordinates.coordinates import Coordinates
from multimodalsim.simulator.stop import TimeCoordinatesLocation, Location
from multimodalsim.simulator.vehicle import Vehicle, Route

logger = logging.getLogger(__name__)


class CoordinatesFromFile(Coordinates):
    def __init__(self, coordinates_file_path: str):
        super().__init__()
        self.__coordinates_file_path = coordinates_file_path
        self.__vehicle_positions_dict = {}
        self.__read_coordinates_from_file()

    def update_position(self, vehicle: Vehicle,
                        route: Route, time: float) -> Location:

        time_positions = None
        if vehicle.id in self.__vehicle_positions_dict:
            time_positions = self.__vehicle_positions_dict[vehicle.id]

        current_position = None
        if time_positions is not None:
            for pos_time, position in time_positions.items():
                if pos_time > time:
                    break
                current_position = position
        elif route is not None \
                and route.current_stop is not None:
            # If no time_positions are available, use location of current_stop.
            current_position = route.current_stop.location
        elif route is not None \
                and len(route.previous_stops) > 0:
            # If current_stop is None, use location of the most recent
            # previous_stops.
            current_position = route.previous_stops[-1].location

        if current_position is not None:
            self.__update_time_dict(current_position, vehicle.id, time)

        return current_position

    def update_polylines(self, route: Route) -> None:
        return None

    def __read_coordinates_from_file(self):
        with open(self.__coordinates_file_path, 'r') as coordinates_file:
            coordinates_reader = csv.reader(coordinates_file,
                                            delimiter=',')
            next(coordinates_reader, None)
            for coordinates_row in coordinates_reader:

                time = int(coordinates_row[1])
                lon = float(coordinates_row[2])
                lat = float(coordinates_row[3])
                time_coordinates = TimeCoordinatesLocation(time, lon, lat)

                vehicle_id_col = coordinates_row[0]
                vehicle_id_list = vehicle_id_col \
                    if type(vehicle_id_col) == list else [vehicle_id_col]

                for vehicle_id in vehicle_id_list:
                    if vehicle_id not in self.__vehicle_positions_dict:
                        self.__vehicle_positions_dict[vehicle_id] = {}

                    self.__vehicle_positions_dict[vehicle_id][time] = \
                        time_coordinates

    def __update_time_dict(self, value, key, time):
        if key not in self.__vehicle_positions_dict:
            self.__vehicle_positions_dict[key] = {}
        self.__vehicle_positions_dict[key][time] = value
