import logging
from typing import Optional

import requests
import polyline
import numpy as np

from multimodalsim.config.coordinates_osrm_config import CoordinatesOSRMConfig
from multimodalsim.coordinates.coordinates import Coordinates
from multimodalsim.simulator.stop import Location, TimeCoordinatesLocation
from multimodalsim.simulator.vehicle import Vehicle, Route

logger = logging.getLogger(__name__)


class CoordinatesOSRM(Coordinates):
    def __init__(self,
                 config: Optional[str | CoordinatesOSRMConfig] = None) -> None:
        super().__init__()

        self.__load_config(config)

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

    def update_polylines(self, route: Route) -> dict[
        str, tuple[str, list[float]]]:

        polylines = {}

        all_stops = []
        all_stops.extend(route.previous_stops)
        if route.current_stop is not None:
            all_stops.append(route.current_stop)
        all_stops.extend(route.next_stops)

        stop_coordinates = [(stop.location.lon, stop.location.lat)
                            for stop in all_stops]
        stop_ids = [stop.location.label for stop in all_stops]

        if len(stop_coordinates) > 2:
            coordinates_str_list = [str(coord[0]) + "," + str(coord[1])
                                    for coord in stop_coordinates]

            service_url = "route/v1/driving/"
            coord_url = ";".join(coordinates_str_list)
            args_url = "?annotations=true&overview=full"

            request_url = self.__osrm_url + service_url + coord_url + args_url

            response = requests.get(request_url)

            res = response.json()

            if res['code'] == 'Ok':
                polylines = \
                    self.__extract_polylines_from_response(res, stop_ids)
            else:
                logger.warning(request_url)
                logger.warning(res)
                polylines = {}
                for i in range(0, len(stop_ids) - 1):
                    coordinates = [stop_coordinates[i],
                                   stop_coordinates[i + 1]]
                    leg_polyline = polyline.encode(coordinates, geojson=True)
                    leg_durations_frac = [1.0]
                    polylines[str(i)] = (leg_polyline, leg_durations_frac)

        else:
            polylines[str(0)] = ("", [])

        return polylines

    def __load_config(self, config):
        if isinstance(config, str):
            config = CoordinatesOSRMConfig(config)
        elif not isinstance(config, CoordinatesOSRMConfig):
            config = CoordinatesOSRMConfig()

        self.__osrm_url = config.url

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

    def __extract_polylines_from_response(self, res, stop_ids):

        polylines = {}

        legs = res['routes'][0]['legs']
        coordinates = polyline.decode(res["routes"][0]["geometry"],
                                      geojson=True)

        if len(legs) != (len(stop_ids) - 1):
            logger.warning("len(legs) ({}) is different from  len(stop_ids) "
                           "({})".format(len(legs), len(stop_ids)))

        start_coord_index = 0
        for leg_index in range(len(legs)):
            leg = legs[leg_index]

            leg_durations = leg['annotation']['duration']
            total_duration = sum(leg_durations)
            leg_durations_frac = [d / total_duration for d in leg_durations] \
                if total_duration > 0 else [1]

            end_coord_index = start_coord_index + len(leg_durations) + 1
            leg_coordinates = coordinates[start_coord_index:end_coord_index]
            leg_polyline = polyline.encode(leg_coordinates, geojson=True)

            polylines[str(leg_index)] = (leg_polyline, leg_durations_frac)

            # The last coordinates of a given leg are the same as the first
            # coordinates of the next leg
            start_coord_index = end_coord_index - 1

        return polylines
