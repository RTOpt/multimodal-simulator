import logging
import csv
import requests
import polyline
import numpy as np
from ast import literal_eval

from multimodalsim.config.coordinates_osrm_config import CoordinatesOSRMConfig
from multimodalsim.simulator.vehicle import TimeCoordinatesLocation

logger = logging.getLogger(__name__)


class Coordinates:

    def __init__(self):
        pass

    def update_position(self, vehicle_id, current_time):
        raise NotImplementedError(
            'Coordinates.update_position not implemented')


class CoordinatesFromFile(Coordinates):
    def __init__(self, coordinates_file_path):
        super().__init__()
        self.__coordinates_file_path = coordinates_file_path
        self.__time_positions_by_vehicle_id = None
        self.__read_coordinates_from_file()

    def update_position(self, vehicle, current_time):

        time_positions = None
        if vehicle.id in self.__time_positions_by_vehicle_id:
            time_positions = self.__time_positions_by_vehicle_id[vehicle.id]

        current_position = None
        if time_positions is not None:
            for time_position in time_positions:
                if time_position.time > current_time:
                    break
                current_position = time_position
        elif vehicle.route is not None \
                and vehicle.route.current_stop is not None:
            # If no time_positions are available, use location of current_stop.
            current_position = vehicle.route.current_stop.location
        elif vehicle.route is not None \
                and len(vehicle.route.previous_stops) > 0:
            # If current_stop is None, use location of the most recent
            # previous_stops.
            current_position = vehicle.route.previous_stops[-1].location

        return current_position

    def __read_coordinates_from_file(self):
        self.__time_positions_by_vehicle_id = {}
        with open(self.__coordinates_file_path, 'r') as coordinates_file:
            coordinates_reader = csv.reader(coordinates_file,
                                            delimiter=',')
            next(coordinates_reader, None)
            for coordinates_row in coordinates_reader:

                time = int(coordinates_row[1])
                lon = float(coordinates_row[2])
                lat = float(coordinates_row[3])
                time_coordinates = TimeCoordinatesLocation(time, lon, lat)

                vehicle_id_col = literal_eval(coordinates_row[0])
                vehicle_id_list = vehicle_id_col \
                    if type(vehicle_id_col) == list else [vehicle_id_col]

                for vehicle_id in vehicle_id_list:
                    if vehicle_id in self.__time_positions_by_vehicle_id:
                        self.__time_positions_by_vehicle_id[vehicle_id].append(
                            time_coordinates)
                    else:
                        self.__time_positions_by_vehicle_id[vehicle_id] = \
                            [time_coordinates]


class CoordinatesOSRM(Coordinates):
    def __init__(self, config=None):
        super().__init__()

        config = CoordinatesOSRMConfig() if config is None else config
        self.__osrm_url = config.url

    def update_position(self, vehicle, current_time):

        current_position = None

        if vehicle.route is None:
            current_position = None
        elif vehicle.route.current_stop is not None:
            current_position = vehicle.route.current_stop.location
        elif len(vehicle.route.previous_stops) > 0:
            # Current position is between two stops
            stop1 = vehicle.route.previous_stops[-1]
            stop2 = vehicle.route.next_stops[0]

            current_coordinates = self.__get_coordinates_from_osrm(
                current_time,
                stop1.departure_time,
                stop1.location.lon,
                stop1.location.lat,
                stop2.arrival_time,
                stop2.location.lon,
                stop2.location.lat)

            current_position = TimeCoordinatesLocation(current_time,
                                                       current_coordinates[0],
                                                       current_coordinates[1])

        return current_position

    def __get_coordinates_from_osrm(self, current_time, time1, lon1, lat1,
                                    time2, lon2, lat2):

        service_url = "route/v1/driving/"
        args_url = "?annotations=true&overview=full"
        coord_url = "{},{};{},{}".format(lon1, lat1, lon2, lat2)

        request_url = self.__osrm_url + service_url + coord_url + args_url

        response = requests.get(request_url)
        route_res = response.json()

        coordinates = polyline.decode(route_res['routes'][0]['geometry'])
        durations = route_res['routes'][0]['legs'][0]['annotation']['duration']
        # We should always have that len(durations) == len(coordinates) - 1

        current_coordinates = \
            self.__calculate_current_coordinates(current_time, time1, time2,
                                                 coordinates, durations)

        return current_coordinates

    def __calculate_current_coordinates(self, current_time, time1, time2,
                                        coordinates, durations):
        current_time_factor = (current_time - time1) / (time2 - time1)
        cumulative_durations = np.cumsum(durations)
        total_duration = cumulative_durations[-1]
        current_duration = current_time_factor * total_duration

        current_i = 0
        for i in range(len(durations)):
            if current_duration >= cumulative_durations[i]:
                current_i = i

        coordinates1 = coordinates[current_i + 1]
        if current_i + 2 < len(coordinates):
            coordinates2 = coordinates[current_i + 2]
            duration1 = cumulative_durations[current_i]
            duration2 = cumulative_durations[current_i + 1]
            current_coordinates = \
                self.__interpolate_coordinates(coordinates1, coordinates2,
                                               duration1, duration2,
                                               current_duration)
        else:
            # Vehicle is at the end of the route (i.e., coordinates1 is the
            # last coordinates)
            current_coordinates = coordinates1

        return current_coordinates

    def __interpolate_coordinates(self, coordinates1, coordinates2, time1,
                                  time2, current_time):
        inter_factor = (current_time - time1) / (time2 - time1)

        current_lon = inter_factor * (coordinates2[0]
                                      - coordinates1[0]) + coordinates1[0]
        current_lat = inter_factor * (coordinates2[1]
                                      - coordinates1[1]) + coordinates1[1]
        current_coordinates = (current_lon, current_lat)

        return current_coordinates
