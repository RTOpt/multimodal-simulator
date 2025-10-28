import json
import logging

import polyline
import numpy as np

from multimodalsim.simulator.stop import TimeCoordinatesLocation, Location
from multimodalsim.simulator.vehicle import Vehicle, Route
from multimodalsim.coordinates.coordinates import Coordinates

logger = logging.getLogger(__name__)


class CoordinatesFromPolylineFile(Coordinates):
    def __init__(self, file_path: str) -> None:
        super().__init__()

        self.polylines = None

        self.__init_polylines_from_file(file_path)

    def update_position(self, vehicle: Vehicle,
                        route: Route, time: float) -> Location:

        current_position = None

        if route.current_stop is not None:
            current_position = route.current_stop.location
        elif len(route.previous_stops) > 0 \
                and vehicle.polylines is not None:
            # Current position is between two stops
            stop1 = route.previous_stops[-1]
            stop2 = route.next_stops[0]
            stop_id = str(len(route.previous_stops) - 1)

            current_coordinates = self.__extract_coordinates_from_polyline(
                vehicle, time, stop1, stop2, stop_id)

            current_position = TimeCoordinatesLocation(time,
                                                       current_coordinates[0],
                                                       current_coordinates[1])

        return current_position

    def update_polylines(self, route: Route) \
            -> dict[str, tuple[str, list[float]]]:

        polylines = {}

        all_stops = []
        all_stops.extend(route.previous_stops)
        if route.current_stop is not None:
            all_stops.append(route.current_stop)
        all_stops.extend(route.next_stops)

        stop_ids = [stop.location.label for stop in all_stops]

        if len(all_stops) > 2:
            for i in range(0, len(stop_ids) - 1):
                stop1 = stop_ids[i]
                stop2 = stop_ids[i + 1]
                leg_polyline = self.polylines[stop1][stop2]
                leg_durations_frac = [1.0]
                polylines[str(i)] = (leg_polyline, leg_durations_frac)
        else:
            polylines[str(0)] = ("", [])

        return polylines

    def __extract_coordinates_from_polyline(self, vehicle, current_time, stop1,
                                            stop2, stop_id):

        stop_polyline_durations = vehicle.polylines[stop_id]

        stop_coordinates = polyline.decode(stop_polyline_durations[0],
                                           geojson=True)
        stop_durations = stop_polyline_durations[1]

        time1 = stop1.departure_time
        time2 = stop2.arrival_time
        current_coordinates = \
            self.__calculate_current_coordinates(current_time, time1, time2,
                                                 stop_coordinates,
                                                 stop_durations)

        return current_coordinates

    def __calculate_current_coordinates(self, current_time, time1, time2,
                                        coordinates, durations_frac):

        current_duration = current_time - time1
        durations = [d * (time2 - time1) for d in durations_frac]
        cumulative_durations = np.cumsum(durations)

        current_i = 0
        for i in range(len(durations_frac)):
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

    def __init_polylines_from_file(self, file_path):

        with open(file_path) as json_data:
            self.polylines = json.load(json_data)
            json_data.close()
