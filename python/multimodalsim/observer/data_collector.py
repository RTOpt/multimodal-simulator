import logging
import pandas as pd

from datetime import datetime

from multimodalsim.simulator.status import PassengersStatus

logger = logging.getLogger(__name__)


class DataCollector:

    def __init__(self):
        pass

    def collect(self, env):
        raise NotImplementedError('DataCollector.collect not implemented')


class StandardDataCollector(DataCollector):

    def __init__(self, data_container=None, vehicles_columns=None,
                 trips_columns=None, events_columns=None):
        super().__init__()

        if data_container is not None:
            self.__data_container = data_container
        else:
            self.__data_container = DataContainer()

        self.__env = None
        self.__event_index = None
        self.__event_priority = None
        self.__current_event = None

        self.__set_vehicles_columns(vehicles_columns)
        self.__set_trips_columns(trips_columns)
        self.__set_events_columns(events_columns)

    @property
    def data_container(self):
        return self.__data_container

    def collect(self, env, current_event=None, event_index=None,
                event_priority=None):
        self.__env = env
        self.__current_event = current_event
        self.__event_priority = event_priority
        self.__event_index = event_index

        self.__collect_vehicles_data()
        self.__collect_trips_data()
        self.__collect_events_data()

    def __set_vehicles_columns(self, vehicles_columns):

        if vehicles_columns is None:
            vehicles_columns = {"id": "id",
                                "time": "time",
                                "status": "status",
                                "previous_stops": "previous_stops",
                                "current_stop": "current_stop",
                                "next_stops": "next_stops",
                                "assigned_legs": "assigned_legs",
                                "onboard_legs": "onboard_legs",
                                "alighted_legs": "alighted_legs"}

        self.__data_container.set_columns("vehicles", vehicles_columns)

    def __set_trips_columns(self, trips_columns):

        if trips_columns is None:
            trips_columns = {"id": "id",
                             "time": "time",
                             "status": "status",
                             "assigned_vehicle": "assigned_vehicle",
                             "current_location": "current_location",
                             "previous_legs": "previous_legs",
                             "current_leg": "current_leg",
                             "next_legs": "next_legs"}

        self.__data_container.set_columns("trips", trips_columns)

    def __set_events_columns(self, events_columns):

        if events_columns is None:
            events_columns = {"name": "name",
                              "time": "time",
                              "priority": "priority",
                              "index": "index"}

        self.__data_container.set_columns("events", events_columns)

    def __collect_vehicles_data(self):

        for vehicle in self.__env.vehicles:
            previous_stops = [str(stop.location) for stop
                              in vehicle.route.previous_stops]
            current_stop = vehicle.route.current_stop.location \
                if vehicle.route.current_stop is not None else None
            next_stops = [str(stop.location) for stop
                          in vehicle.route.next_stops]

            assigned_legs = [leg.id for leg in vehicle.route.assigned_legs]
            onboard_legs = [leg.id for leg in vehicle.route.onboard_legs]
            alighted_legs = [leg.id for leg in vehicle.route.alighted_legs]

            time = datetime.fromtimestamp(self.__current_event.time)
            obs_dict = {"id": vehicle.id,
                        "time": time,
                        "status": vehicle.route.status,
                        "previous_stops": previous_stops,
                        "current_stop": str(current_stop),
                        "next_stops": next_stops,
                        "assigned_legs": assigned_legs,
                        "onboard_legs": onboard_legs,
                        "alighted_legs": alighted_legs}

            self.__data_container.add_observation(
                "vehicles", obs_dict, "id",
                no_rep_on_keys=["id", "time"])

    def __collect_trips_data(self):
        for trip in self.__env.trips:
            assigned_vehicle_id = self.__get_assigned_vehicle_id(trip)
            current_location = self.__get_current_location(trip)

            previous_legs = [(str(leg.origin), str(leg.destination)) for leg
                             in trip.previous_legs] \
                if trip.previous_legs is not None else None
            current_leg = (str(trip.current_leg.origin),
                           str(trip.current_leg.destination))

            next_legs = [(str(leg.origin), str(leg.destination)) for leg
                         in trip.next_legs] \
                if trip.next_legs is not None else None

            time = datetime.fromtimestamp(self.__current_event.time)
            obs_dict = {"id": trip.id,
                        "time": time,
                        "status": trip.status,
                        "assigned_vehicle": str(assigned_vehicle_id),
                        "current_location": str(current_location),
                        "previous_legs": previous_legs,
                        "current_leg": current_leg,
                        "next_legs": next_legs}
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

        event_name = self.__current_event.name
        event_time = datetime.fromtimestamp(self.__current_event.time)

        obs_dict = {"name": event_name,
                    "time": event_time,
                    "priority": self.__event_priority,
                    "index": self.__event_index}
        self.__data_container.add_observation("events", obs_dict, "index")


class DataContainer:

    def __init__(self):
        self.__observations_tables = {}
        self.__observations_tables_dfs = {}
        self.__dfs_columns = {}

    @property
    def observations_tables(self):
        return self.__observations_tables

    def get_observations_table_df(self, table_name):
        return self.__observations_tables_dfs[table_name]

    def get_columns(self, table_name):
        return self.__dfs_columns[table_name]

    def set_columns(self, table_name, columns):
        self.__dfs_columns[table_name] = columns

    def add_observation(self, table_name, obs_dict, obs_id_key,
                        no_rep_on_keys=None):
        logger.debug("table_name={}, row_dict={}, obs_id_key={}, "
                     "no_rep_on_keys={}".format(table_name, obs_dict,
                                                obs_id_key, no_rep_on_keys))

        if no_rep_on_keys is None \
                or self.__can_add_obs_to_table(table_name, obs_dict,
                                               obs_id_key, no_rep_on_keys):
            self.__add_obs_to_dict(table_name, obs_dict, obs_id_key)
            self.__add_obs_to_df(table_name, obs_dict)

    def save_observations_to_csv(self, table_name, file_name):

        self.__observations_tables_dfs[table_name].to_csv(file_name,
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
            self.__observations_tables[table_name] = {}

        obs_id = row_dict[obs_id_key]
        if obs_id not in self.__observations_tables[table_name]:
            self.__observations_tables[table_name][obs_id] = []

        self.__observations_tables[table_name][obs_id].append(row_dict)

    def __add_obs_to_df(self, table_name, row_dict):
        if table_name not in self.__observations_tables_dfs:
            self.__observations_tables_dfs[table_name] = pd.DataFrame()

        row_df = self.__convert_row_dict_to_df(table_name, row_dict)

        self.__observations_tables_dfs[table_name] = pd.concat(
            [self.__observations_tables_dfs[table_name], row_df],
            ignore_index=True)

    def __convert_row_dict_to_df(self, table_name, row_dict):

        df_columns = [self.__dfs_columns[table_name][x]
                      for x in row_dict.keys()]

        return pd.DataFrame([row_dict.values()], columns=df_columns)
