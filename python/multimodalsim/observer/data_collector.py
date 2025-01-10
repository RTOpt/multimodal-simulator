import logging
from typing import Optional

import pandas as pd

import multimodalsim.simulator.request
import multimodalsim.simulator.vehicle
import multimodalsim.simulator.passenger_event
import multimodalsim.simulator.vehicle_event
from multimodalsim.config.data_collector_config import DataCollectorConfig
from multimodalsim.simulator.event import ActionEvent, Event
from multimodalsim.state_machine.status import PassengerStatus
import multimodalsim.simulator.environment as environment

logger = logging.getLogger(__name__)


class DataCollector:

    def __init__(self) -> None:
        pass

    def collect(self, env: 'environment.Environment',
                current_event: Optional[Event] = None,
                event_index: Optional[int] = None,
                event_priority: Optional[int] = None) -> None:
        raise NotImplementedError('DataCollector.collect not implemented')


class StandardDataCollector(DataCollector):

    def __init__(self, data_container: Optional['DataContainer'] = None,
                 config: Optional[str | DataCollectorConfig] = None) -> None:
        super().__init__()

        self.__data_container = DataContainer() if data_container is None \
            else data_container

        self.__env = None
        self.__event_index = None
        self.__event_priority = None
        self.__current_event = None
        self.__time = None

        self.__load_config(config)

    @property
    def data_container(self) -> 'DataContainer':
        return self.__data_container

    def collect(self, env: 'environment.Environment',
                current_event: Optional[Event] = None,
                event_index: Optional[int] = None,
                event_priority: Optional[int] = None) -> None:
        self.__env = env
        self.__current_event = current_event
        self.__event_priority = event_priority
        self.__event_index = event_index
        self.__time = self.__current_event.time \
            if self.__current_event is not None else self.__env.current_time

        if (isinstance(current_event, ActionEvent)
                and isinstance(current_event.state_machine.owner,
                               multimodalsim.simulator.request.Trip)):
            self.__collect_trips_data(current_event.state_machine.owner)
        elif hasattr(current_event, "trip"):
            self.__collect_trips_data(current_event.trip)
        elif isinstance(current_event, ActionEvent) \
                and isinstance(current_event.state_machine.owner,
                               multimodalsim.simulator.vehicle.Vehicle):
            vehicle = current_event.state_machine.owner
            self.__collect_vehicles_data(vehicle)
        elif hasattr(current_event, "vehicle"):
            self.__collect_vehicles_data(current_event.vehicle)

        self.__collect_events_data()

        self.__collect_environment_data(env)

    def __load_config(self, config):
        if isinstance(config, str):
            config = DataCollectorConfig(config)
        elif not isinstance(config, DataCollectorConfig):
            config = DataCollectorConfig()

        self.__data_container.set_columns("vehicles",
                                          config.get_vehicles_columns())
        self.__data_container.set_columns("trips",
                                          config.get_trips_columns())
        self.__data_container.set_columns("events",
                                          config.get_events_columns())

    def __collect_vehicles_data(self, vehicle):

        route = self.__env.get_route_by_vehicle_id(vehicle.id)

        previous_stops = [str(stop.location) for stop
                          in route.previous_stops]
        current_stop_loc = route.current_stop.location \
            if route.current_stop is not None else None
        next_stops = [str(stop.location) for stop
                      in route.next_stops]

        assigned_legs = [leg.id for leg in route.assigned_legs]
        onboard_legs = [leg.id for leg in route.onboard_legs]
        alighted_legs = [leg.id for leg in route.alighted_legs]

        cumulative_distance = route.current_stop.cumulative_distance \
            if route.current_stop is not None else None

        stop_lon = current_stop_loc.lon \
            if current_stop_loc is not None else None
        stop_lat = current_stop_loc.lat \
            if current_stop_loc is not None else None
        lon = vehicle.position.lon if vehicle.position is not None else stop_lon
        lat = vehicle.position.lat if vehicle.position is not None else stop_lat

        polylines = vehicle.polylines \
            if vehicle.polylines is not None and len(vehicle.polylines) > 0 \
            else None

        mode = vehicle.mode if vehicle.mode is not None else ""

        obs_dict = {"id": vehicle.id,
                    "time": self.__time,
                    "status": vehicle.status,
                    "previous_stops": previous_stops,
                    "current_stop": str(current_stop_loc),
                    "next_stops": next_stops,
                    "assigned_legs": assigned_legs,
                    "onboard_legs": onboard_legs,
                    "alighted_legs": alighted_legs,
                    "cumulative_distance": cumulative_distance,
                    "stop_lon": stop_lon,
                    "stop_lat": stop_lat,
                    "lon": lon,
                    "lat": lat,
                    "polylines": polylines,
                    "mode": mode}

        self.__data_container.add_observation(
            "vehicles", obs_dict, "id")

        self.__update_trip_cumulative_distance_by_vehicle(vehicle, route)

    def __update_trip_cumulative_distance_by_vehicle(self, vehicle, route):

        if "trips_cumulative_distance" \
                not in self.__data_container.observations_tables:
            self.__data_container.observations_tables[
                "trips_cumulative_distance"] = {}

        cumdist_by_veh_by_trip = self.__data_container.observations_tables[
                "trips_cumulative_distance"]

        if route.current_stop is not None:
            current_veh_cumdist = route.current_stop.cumulative_distance
        else:
            current_veh_cumdist = route.previous_stops[-1].cumulative_distance

        for leg in route.assigned_legs:

            trip = leg.trip

            if trip.id not in cumdist_by_veh_by_trip:
                cumdist_by_veh_by_trip[trip.id] = {}

            if vehicle.id not in cumdist_by_veh_by_trip[trip.id]:
                cumdist_by_veh_by_trip[trip.id][vehicle.id] = \
                    {"cumdist": 0, "veh_cumdist": current_veh_cumdist}
            elif current_veh_cumdist is not None:
                cumdist_by_veh_by_trip[trip.id][vehicle.id]["cumdist"] += \
                    current_veh_cumdist \
                    - cumdist_by_veh_by_trip[trip.id][vehicle.id][
                        "veh_cumdist"]
                cumdist_by_veh_by_trip[trip.id][vehicle.id]["veh_cumdist"] = \
                    current_veh_cumdist
            else:
                cumdist_by_veh_by_trip[trip.id][vehicle.id]["cumdist"] = None

                cumdist_by_veh_by_trip[trip.id][vehicle.id][
                    "veh_cumdist"] = None

    def __collect_trips_data(self, trip):

        assigned_vehicle_id = self.__get_assigned_vehicle_id(trip)
        current_location = self.__get_current_location(trip)

        previous_legs = [(str(leg.origin), str(leg.destination)) for leg
                         in trip.previous_legs] \
            if trip.previous_legs is not None else None

        if trip.current_leg is not None:
            current_leg = (str(trip.current_leg.origin),
                           str(trip.current_leg.destination))

            next_legs = [(str(leg.origin), str(leg.destination)) for leg
                         in trip.next_legs] \
                if trip.next_legs is not None else []

        elif len(trip.next_legs) > 0:
            current_leg = (str(trip.next_legs[0].origin),
                           str(trip.next_legs[0].destination))

            next_legs = [(str(leg.origin), str(leg.destination)) for leg
                         in trip.next_legs[1:]] \
                if len(trip.next_legs) > 1 else []
        else:
            current_leg = None

            next_legs = [(str(leg.origin), str(leg.destination)) for leg
                         in trip.next_legs] \
                if trip.next_legs is not None else []

        name = trip.name if trip.name is not None else trip.id

        obs_dict = {"id": trip.id,
                    "time": self.__time,
                    "status": trip.status,
                    "assigned_vehicle": str(assigned_vehicle_id),
                    "current_location": str(current_location),
                    "previous_legs": previous_legs,
                    "current_leg": current_leg,
                    "next_legs": next_legs,
                    "name": name}

        self.__data_container.add_observation("trips", obs_dict, "id")

        self.__update_trip_cumulative_distance_by_trip(trip)

    def __get_assigned_vehicle_id(self, trip):
        if trip.current_leg is not None \
                and trip.current_leg.assigned_vehicle is not None:
            assigned_vehicle_id = trip.current_leg.assigned_vehicle.id
        elif len(trip.next_legs) > 0 \
                and trip.next_legs[0].assigned_vehicle is not None:
            assigned_vehicle_id = trip.next_legs[0].assigned_vehicle.id
        else:
            assigned_vehicle_id = None

        return assigned_vehicle_id

    def __get_current_location(self, trip):

        current_location = None
        if trip.current_leg is not None \
                and trip.status in [PassengerStatus.RELEASE,
                                    PassengerStatus.ASSIGNED,
                                    PassengerStatus.READY]:
            current_location = trip.current_leg.origin
        elif trip.current_leg is not None \
                and trip.status == PassengerStatus.COMPLETE:
            current_location = trip.current_leg.destination
        elif len(trip.next_legs) > 0:
            current_location = trip.next_legs[0].origin
        elif len(trip.previous_legs) > 0:
            current_location = trip.previous_legs[0].destination

        return current_location

    def __update_trip_cumulative_distance_by_trip(self, trip):

        if "trips_cumulative_distance" \
                not in self.__data_container.observations_tables:
            self.__data_container.observations_tables[
                "trips_cumulative_distance"] = {}

        cumdist_by_veh_by_trip = self.__data_container.observations_tables[
                "trips_cumulative_distance"]
        if trip.current_leg is not None \
                and trip.current_leg.assigned_vehicle is not None:
            veh = trip.current_leg.assigned_vehicle
            route = self.__env.get_route_by_vehicle_id(veh.id)

            if route.current_stop is not None:
                current_veh_cumdist = \
                    route.current_stop.cumulative_distance
            else:
                current_veh_cumdist = \
                    route.previous_stops[-1].cumulative_distance

            if trip.id not in cumdist_by_veh_by_trip:
                cumdist_by_veh_by_trip[trip.id] = {}

            if veh.id not in cumdist_by_veh_by_trip[trip.id]:
                cumdist_by_veh_by_trip[trip.id][veh.id] = \
                    {"cumdist": 0, "veh_cumdist": current_veh_cumdist}
            elif current_veh_cumdist is not None:
                cumdist_by_veh_by_trip[trip.id][veh.id]["cumdist"] += \
                    current_veh_cumdist \
                    - cumdist_by_veh_by_trip[trip.id][veh.id]["veh_cumdist"]
                cumdist_by_veh_by_trip[trip.id][veh.id]["veh_cumdist"] = \
                    current_veh_cumdist
            else:
                cumdist_by_veh_by_trip[trip.id][veh.id]["cumdist"] = None
                cumdist_by_veh_by_trip[trip.id][veh.id]["veh_cumdist"] = None

    def __collect_events_data(self):

        event_name = self.__current_event.name \
            if self.__current_event is not None else None

        obs_dict = {"name": event_name,
                    "time": self.__time,
                    "priority": self.__event_priority,
                    "index": self.__event_index}
        self.__data_container.add_observation("events", obs_dict, "index")

    def __collect_environment_data(self, env):

        trips_by_mode = {None: 0}
        active_trips_by_mode = {None: 0}
        for trip in env.trips:
            self.__collect_total_nb_trips(trip, trips_by_mode)
            self.__collect_nb_active_trips(trip, active_trips_by_mode)

        self.__data_container.observations_tables["total_nb_trips_by_mode"] \
            = trips_by_mode
        self.__data_container.observations_tables["nb_active_trips_by_mode"] \
            = active_trips_by_mode

    def __collect_total_nb_trips(self, trip, trips_by_mode):

        trips_by_mode[None] += 1
        trip_modes = set()
        for leg in trip.previous_legs:
            trip_modes.add(leg.assigned_vehicle.mode)
        if trip.current_leg is not None \
                and trip.current_leg.assigned_vehicle is not None:
            mode = trip.current_leg.assigned_vehicle.mode
            trip_modes.add(mode)
        for mode in trip_modes:
            trips_by_mode[mode] = trips_by_mode[mode] + 1 \
                if mode in trips_by_mode else 1

    def __collect_nb_active_trips(self, trip, active_trips_by_mode):

        if trip.status != PassengerStatus.COMPLETE:
            active_trips_by_mode[None] += 1
            if trip.current_leg is not None \
                    and trip.current_leg.assigned_vehicle is not None:
                mode = trip.current_leg.assigned_vehicle.mode
                if mode not in active_trips_by_mode:
                    active_trips_by_mode[mode] = 1
                else:
                    active_trips_by_mode[mode] += 1


class DataContainer:

    def __init__(self) -> None:
        self.__observations_tables = {}
        self.__observations_tables_dfs = {}
        self.__dfs_columns = {}

        self.__updated_dfs = {}

    @property
    def observations_tables(self) -> dict:
        return self.__observations_tables

    def get_observations_table_df(self, table_name: str) -> pd.DataFrame:

        if not self.__updated_dfs[table_name]:
            self.__convert_obs_table_to_df(table_name)

        return self.__observations_tables_dfs[table_name]

    def get_columns(self, table_name: str) -> dict:
        return self.__dfs_columns[table_name]

    def set_columns(self, table_name: str, columns: dict):
        self.__dfs_columns[table_name] = columns

    def add_observation(self, table_name: str, obs_dict: dict,
                        obs_id_key: Optional[str] = None):
        self.__add_obs_to_dict(table_name, obs_dict, obs_id_key)
        self.__updated_dfs[table_name] = False

    def save_observations_to_csv(self, table_name: str, file_name: str):

        self.get_observations_table_df(table_name).to_csv(file_name,
                                                          index=False)

    def __can_add_obs_to_table(self, table_name, obs_dict, obs_id_key,
                               no_rep_on_keys):
        obs_id = obs_dict[obs_id_key]

        can_add_obs = False
        if table_name not in self.__observations_tables:
            can_add_obs = True
        elif obs_id not in self.__observations_tables[table_name]:
            can_add_obs = True
        else:
            for no_rep_key in set(obs_dict.keys()) - set(no_rep_on_keys):
                if obs_dict[no_rep_key] != \
                        self.__observations_tables[table_name][obs_id][-1][
                            no_rep_key]:
                    can_add_obs = True

        return can_add_obs

    def __add_obs_to_dict(self, table_name, row_dict, obs_id_key):

        if table_name not in self.__observations_tables:
            self.__observations_tables[table_name] = []
        self.__observations_tables[table_name].append(row_dict)

    def __add_obs_to_df(self, table_name, row_dict):
        if table_name not in self.__observations_tables_dfs:
            self.__observations_tables_dfs[table_name] = pd.DataFrame()

        row_df = self.__convert_row_dict_to_df(table_name, row_dict)

        self.__observations_tables_dfs[table_name] = pd.concat(
            [self.__observations_tables_dfs[table_name], row_df],
            ignore_index=True)

    def __convert_obs_table_to_df(self, table_name):

        self.__observations_tables_dfs[table_name] = \
            pd.DataFrame(self.__observations_tables[table_name])
        self.__observations_tables_dfs[table_name].columns = \
            [x.replace(x, self.__dfs_columns[table_name][x])
             for x in self.__observations_tables_dfs[table_name].columns]

        self.__updated_dfs[table_name] = True

    def __convert_row_dict_to_df(self, table_name, row_dict):

        df_columns = [self.__dfs_columns[table_name][x]
                      for x in row_dict.keys()]

        return pd.DataFrame([row_dict.values()], columns=df_columns)
