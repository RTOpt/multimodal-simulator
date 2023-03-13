import logging
import pandas as pd

import multimodalsim.simulator.request
import multimodalsim.simulator.vehicle
import multimodalsim.simulator.passenger_event
import multimodalsim.simulator.vehicle_event
from multimodalsim.config.data_collector_config import DataCollectorConfig
from multimodalsim.simulator.event import ActionEvent
from multimodalsim.state_machine.status import PassengersStatus

logger = logging.getLogger(__name__)


class DataCollector:

    def __init__(self):
        pass

    def collect(self, env):
        raise NotImplementedError('DataCollector.collect not implemented')


class StandardDataCollector(DataCollector):

    def __init__(self, data_container=None, config=None):
        super().__init__()

        self.__data_container = DataContainer() if data_container is None \
            else data_container

        self.__env = None
        self.__event_index = None
        self.__event_priority = None
        self.__current_event = None
        self.__time = None

        config = DataCollectorConfig() if config is None else config
        self.__load_config(config)

    @property
    def data_container(self):
        return self.__data_container

    def collect(self, env, current_event=None, event_index=None,
                event_priority=None):
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
                               multimodalsim.simulator.vehicle.Route):
            self.__collect_vehicles_data(current_event.state_machine.owner)
        elif hasattr(current_event, "vehicle"):
            self.__collect_vehicles_data(current_event.vehicle.route)

        self.__collect_events_data()

    def __load_config(self, config):
        self.__data_container.set_columns("vehicles",
                                          config.get_vehicles_columns())
        self.__data_container.set_columns("trips",
                                          config.get_trips_columns())
        self.__data_container.set_columns("events",
                                          config.get_events_columns())

    def __collect_vehicles_data(self, route):

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
        lon = route.vehicle.position.lon \
            if route.vehicle.position is not None else None
        lat = route.vehicle.position.lat \
            if route.vehicle.position is not None else None

        past_polyline = route.vehicle.past_polyline
        future_polyline = route.vehicle.future_polyline

        obs_dict = {"id": route.vehicle.id,
                    "time": self.__time,
                    "status": route.status,
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
                    "past_polyline": past_polyline,
                    "future_polyline": future_polyline}

        self.__data_container.add_observation(
            "vehicles", obs_dict, "id",
            no_rep_on_keys=["id", "time"])

    def __collect_trips_data(self, trip):

        assigned_vehicle_id = self.__get_assigned_vehicle_id(trip)
        current_location = self.__get_current_location(trip)

        previous_legs = [(str(leg.origin), str(leg.destination)) for leg
                         in trip.previous_legs] \
            if trip.previous_legs is not None else None
        current_leg = (str(trip.current_leg.origin),
                       str(trip.current_leg.destination)) \
            if trip.current_leg is not None else None

        next_legs = [(str(leg.origin), str(leg.destination)) for leg
                     in trip.next_legs] \
            if trip.next_legs is not None else None

        lon = trip.position.lon \
            if trip.position is not None else None
        lat = trip.position.lat \
            if trip.position is not None else None

        past_polyline = trip.past_polyline
        future_polyline = trip.future_polyline

        obs_dict = {"id": trip.id,
                    "time": self.__time,
                    "status": trip.status,
                    "assigned_vehicle": str(assigned_vehicle_id),
                    "current_location": str(current_location),
                    "previous_legs": previous_legs,
                    "current_leg": current_leg,
                    "next_legs": next_legs,
                    "lon": lon,
                    "lat": lat,
                    "past_polyline": past_polyline,
                    "future_polyline": future_polyline}

        self.__data_container.add_observation("trips", obs_dict, "id",
                                              no_rep_on_keys=["id",
                                                              "time"])

    def __get_assigned_vehicle_id(self, trip):
        if trip.current_leg is not None \
                and trip.current_leg.assigned_vehicle is not None:
            assigned_vehicle_id = trip.current_leg.assigned_vehicle.id
        else:
            assigned_vehicle_id = None

        return assigned_vehicle_id

    def __get_current_location(self, trip):

        current_location = None
        if trip.current_leg is not None \
                and trip.status in [PassengersStatus.RELEASE,
                                    PassengersStatus.ASSIGNED,
                                    PassengersStatus.READY]:
            current_location = trip.current_leg.origin
        elif trip.current_leg is not None \
                and trip.status == PassengersStatus.COMPLETE:
            current_location = trip.current_leg.destination

        return current_location

    def __collect_events_data(self):

        event_name = self.__current_event.name \
            if self.__current_event is not None else None

        obs_dict = {"name": event_name,
                    "time": self.__time,
                    "priority": self.__event_priority,
                    "index": self.__event_index}
        self.__data_container.add_observation("events", obs_dict, "index")


class DataContainer:

    def __init__(self):
        self.__observations_tables = {}
        self.__observations_tables_dfs = {}
        self.__dfs_columns = {}

        self.__updated_dfs = {}

    @property
    def observations_tables(self):
        return self.__observations_tables

    def get_observations_table_df(self, table_name):

        if not self.__updated_dfs[table_name]:
            self.__convert_obs_table_to_df(table_name)

        return self.__observations_tables_dfs[table_name]

    def get_columns(self, table_name):
        return self.__dfs_columns[table_name]

    def set_columns(self, table_name, columns):
        self.__dfs_columns[table_name] = columns

    def add_observation(self, table_name, obs_dict, obs_id_key,
                        no_rep_on_keys=None):

        # if no_rep_on_keys is None \
        #         or self.__can_add_obs_to_table(table_name, obs_dict,
        #                                        obs_id_key, no_rep_on_keys):
        self.__add_obs_to_dict(table_name, obs_dict, obs_id_key)
        self.__updated_dfs[table_name] = False
        # self.__add_obs_to_df(table_name, obs_dict)

    def save_observations_to_csv(self, table_name, file_name):

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

        # if table_name not in self.__observations_tables:
        #     self.__observations_tables[table_name] = {}
        #
        # obs_id = row_dict[obs_id_key]
        # if obs_id not in self.__observations_tables[table_name]:
        #     self.__observations_tables[table_name][obs_id] = []
        #
        # self.__observations_tables[table_name][obs_id].append(row_dict)

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
