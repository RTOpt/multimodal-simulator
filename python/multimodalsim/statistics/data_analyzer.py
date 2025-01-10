from typing import Optional

import pandas as pd
import logging

from multimodalsim.config.data_analyzer_config import DataAnalyzerConfig
from multimodalsim.observer.data_collector import DataContainer
from multimodalsim.state_machine.status import PassengerStatus, VehicleStatus

logger = logging.getLogger(__name__)


class DataAnalyzer:

    def __init__(self, data_container: Optional[DataContainer] = None) -> None:
        self.__data_container = data_container

        pd.set_option('display.max_rows', 50)
        pd.set_option('display.max_columns', 50)

    @property
    def data_container(self) -> Optional[DataContainer]:
        return self.__data_container

    @data_container.setter
    def data_container(self, data_container: Optional[DataContainer]) -> None:
        self.__data_container = data_container

    def get_description(self, table_name: str) -> pd.DataFrame:
        observations_df = self.data_container \
            .get_observations_table_df(table_name)

        return observations_df.describe(include='all')

    @property
    def modes(self) -> list[str]:
        raise NotImplementedError("DataAnalyzer.modes has not been "
                                  "implemented")

    def get_statistics(self):
        raise NotImplementedError("DataAnalyzer.get_statistics has not been "
                                  "implemented")

    def get_vehicles_statistics(self, mode: Optional[str] = None) -> dict:
        raise NotImplementedError("DataAnalyzer.get_vehicles_statistics has "
                                  "not been implemented")

    def get_trips_statistics(self, mode: Optional[str] = None) -> dict:
        raise NotImplementedError("DataAnalyzer.get_trips_statistics has "
                                  "not been implemented")


class FixedLineDataAnalyzer(DataAnalyzer):

    def __init__(self, data_container: Optional[DataContainer] = None,
                 config: Optional[DataAnalyzerConfig] = None):
        super().__init__(data_container)

        self.__load_config(config)

    @property
    def nb_events(self) -> int:
        return len(self.data_container.get_observations_table_df(
            self.__events_table_name))

    @property
    def nb_event_types(self) -> int:
        name_col = self.data_container.get_columns("events")["name"]
        return len(self.data_container.get_observations_table_df(
            self.__events_table_name).groupby(name_col))

    @property
    def nb_events_by_type(self) -> pd.Series:
        name_col = self.data_container.get_columns("events")["name"]
        return self.data_container.get_observations_table_df(
            self.__events_table_name)[name_col].value_counts().sort_index()

    @property
    def modes(self) -> list[str]:
        modes = []
        if "vehicles" in self.data_container.observations_tables:
            vehicles_df = self.data_container.get_observations_table_df(
                self.__vehicles_table_name)
            mode_col = self.data_container.get_columns("vehicles")["mode"]
            modes = list(vehicles_df.groupby(mode_col).groups.keys())

        return modes

    @property
    def modes_by_vehicle(self) -> dict[str, str]:
        modes_by_vehicle = {}
        if "vehicles" in self.data_container.observations_tables:
            vehicles_df = self.data_container.get_observations_table_df(
                self.__vehicles_table_name)
            id_col = self.data_container.get_columns("vehicles")["id"]
            mode_col = self.data_container.get_columns("vehicles")["mode"]
            modes_by_vehicle = \
                dict(vehicles_df.groupby(id_col)[mode_col].first())

        return modes_by_vehicle

    def get_total_nb_trips(self, mode: Optional[str] = None) -> int:
        nb_trips = 0
        if "total_nb_trips_by_mode" in self.data_container.observations_tables:
            trips_by_mode = self.data_container.observations_tables[
                "total_nb_trips_by_mode"]
            if mode in trips_by_mode:
                nb_trips = trips_by_mode[mode]

        return nb_trips

    def get_nb_active_trips(self, mode: Optional[str] = None) -> int:
        nb_trips = 0
        if "nb_active_trips_by_mode" \
                in self.data_container.observations_tables:
            active_trips_by_mode = self.data_container.observations_tables[
                "nb_active_trips_by_mode"]
            if mode in active_trips_by_mode:
                nb_trips = active_trips_by_mode[mode]

        return nb_trips

    def get_total_nb_vehicles(self, mode: Optional[str] = None) -> int:
        nb_vehicles = 0
        if "vehicles" in self.data_container.observations_tables:
            vehicles_df = self.data_container.get_observations_table_df(
                self.__vehicles_table_name)
            id_col = self.data_container.get_columns("vehicles")["id"]

            if mode is not None:
                mode_col = self.data_container.get_columns("vehicles")["mode"]
                vehicles_grouped_by_mode = vehicles_df.groupby(mode_col)
                vehicles_df = vehicles_grouped_by_mode.get_group(mode)

            nb_vehicles = len(vehicles_df.groupby(id_col))

        return nb_vehicles

    def get_nb_active_vehicles(self, mode: Optional[str] = None) -> int:
        nb_vehicles = 0
        if "vehicles" in self.data_container.observations_tables:
            vehicles_df = self.data_container.get_observations_table_df(
                self.__vehicles_table_name)
            id_col = self.data_container.get_columns("vehicles")["id"]

            if mode is not None:
                mode_col = self.data_container.get_columns("vehicles")["mode"]
                vehicles_grouped_by_mode = vehicles_df.groupby(mode_col)
                vehicles_df = vehicles_grouped_by_mode.get_group(mode)

            status_by_veh_id_series = vehicles_df.groupby(id_col)[
                "Status"].unique()
            incomplete_mask = status_by_veh_id_series.apply(
                lambda x: VehicleStatus.COMPLETE not in x)

            nb_vehicles = len(status_by_veh_id_series[incomplete_mask])

        return nb_vehicles

    def get_vehicles_distance_travelled(
            self, mode: Optional[str] = None) -> float:
        total_dist = 0
        if "vehicles" in self.data_container.observations_tables:
            vehicles_df = self.data_container.get_observations_table_df(
                self.__vehicles_table_name)
            id_col = self.data_container.get_columns("vehicles")["id"]

            if mode is not None:
                mode_col = self.data_container.get_columns("vehicles")["mode"]
                vehicles_grouped_by_mode = vehicles_df.groupby(mode_col)
                vehicles_df = vehicles_grouped_by_mode.get_group(mode)

            cumulative_distance_col = \
                self.data_container.get_columns("vehicles")[
                    "cumulative_distance"]
            total_dist = \
                vehicles_df.groupby(id_col).last()[
                    cumulative_distance_col].sum()

        return total_dist

    def get_trips_distance_travelled(
            self, mode: Optional[str] = None) -> float:
        total_dist = 0
        if "trips_cumulative_distance" \
                in self.data_container.observations_tables:
            cumdist_by_veh_by_trip = \
                self.data_container.observations_tables[
                    "trips_cumulative_distance"]

            modes_by_veh = self.modes_by_vehicle

            for trip_id, veh_dict in cumdist_by_veh_by_trip.items():
                for veh_id, cumdist_dict in veh_dict.items():
                    if (mode is None) or (mode == modes_by_veh[veh_id]):
                        total_dist += cumdist_dict["cumdist"] \
                            if cumdist_dict["cumdist"] is not None else 0

        return total_dist

    def get_total_ghg_e(self, mode: Optional[str] = None) -> float:

        total_distance_travelled = self.get_vehicles_distance_travelled(mode)

        return total_distance_travelled * self.__default_ghg_e

    def get_statistics(self):

        statistics = {
            "trips": {mode: self.get_trips_statistics(mode)
                      for mode in self.modes},
            "vehicles": {mode: self.get_vehicles_statistics(mode)
                         for mode in self.modes}
        }

        return statistics

    def get_vehicles_statistics(self, mode: Optional[str] = None) -> dict:

        nb_vehicles = self.get_total_nb_vehicles(mode)
        nb_active_vehicles = self.get_nb_active_vehicles(mode)
        total_distance_travelled = self.get_vehicles_distance_travelled(mode)
        ghg_e = self.get_total_ghg_e(mode)

        vehicles_statistics = {
            "Total number of vehicles": nb_vehicles,
            "Number of active vehicles": nb_active_vehicles,
            "Distance travelled": total_distance_travelled,
            "Greenhouse gas emissions": ghg_e
        }

        return vehicles_statistics

    def get_trips_statistics(self, mode: Optional[str] = None) -> dict:

        nb_trips = self.get_total_nb_trips(mode)
        nb_active_trips = self.get_nb_active_trips(mode)
        total_distance_travelled = self.get_trips_distance_travelled(mode)

        vehicles_statistics = {
            "Total number of trips": nb_trips,
            "Number of active trips": nb_active_trips,
            "Distance travelled": total_distance_travelled
        }

        return vehicles_statistics

    def get_vehicle_status_duration_statistics(self) -> pd.DataFrame:
        vehicles_df = self.data_container.get_observations_table_df(
            self.__vehicles_table_name)
        return self.__generate_status_duration_stats(vehicles_df, "vehicles")

    def get_trip_status_duration_statistics(self) -> pd.DataFrame:
        trips_df = self.data_container.get_observations_table_df(
            self.__trips_table_name)
        return self.__generate_status_duration_stats(trips_df, "trips")

    def get_boardings_alightings_stats(self) -> pd.DataFrame:
        trips_df = self.data_container.get_observations_table_df(
            self.__trips_table_name)
        status_col = self.data_container.get_columns("trips")["status"]
        previous_legs_col = self.data_container.get_columns("trips")[
            "previous_legs"]

        trips_complete_series = trips_df[trips_df[status_col]
                                         == PassengerStatus.COMPLETE]

        trips_legs_complete_series = trips_complete_series.apply(
            lambda x: x[previous_legs_col], axis=1)

        nb_boardings_by_stop = {}
        trips_legs_complete_series.map(
            lambda x: self.__get_nb_boardings_by_stop(x, nb_boardings_by_stop))

        nb_alightings_by_stop = {}
        trips_legs_complete_series.map(
            lambda x: self.__get_nb_alightings_by_stop(x,
                                                       nb_alightings_by_stop))

        nb_boardings_by_stop_df = pd.DataFrame(
            nb_boardings_by_stop, index=['Nb. Boardings']).transpose()

        nb_alightings_by_stop_df = pd.DataFrame(
            nb_alightings_by_stop, index=['Nb. Alightings']).transpose()

        boardings_alightings_stats_df = pd.merge(
            nb_boardings_by_stop_df, nb_alightings_by_stop_df,
            left_index=True, right_index=True, how='outer')

        return boardings_alightings_stats_df

    def get_max_load_by_vehicle(self) -> pd.DataFrame:
        vehicles_df = self.data_container.get_observations_table_df(
            self.__vehicles_table_name)
        onboard_legs_col = self.data_container.get_columns("vehicles")[
            "onboard_legs"]
        id_col = self.data_container.get_columns("vehicles")["id"]

        vehicles_load_df = vehicles_df.copy()
        vehicles_load_df["max load"] = vehicles_load_df[onboard_legs_col]. \
            apply(len)
        vehicles_max_load_df = vehicles_load_df.groupby(id_col). \
            agg({"max load": max})
        return vehicles_max_load_df

    def get_nb_legs_by_trip_stats(self) -> pd.DataFrame:
        trips_df = self.data_container.get_observations_table_df(
            self.__trips_table_name)
        id_col = self.data_container.get_columns("trips")["id"]
        status_col = self.data_container.get_columns("trips")["status"]
        previous_legs_col = self.data_container.get_columns("trips")[
            "previous_legs"]

        trips_complete_series = trips_df[trips_df[status_col]
                                         == VehicleStatus.COMPLETE]
        trips_legs_complete_series = trips_complete_series.apply(
            lambda x: x[previous_legs_col], axis=1)

        nb_legs_by_trip_df = trips_df[
            trips_df[status_col] == VehicleStatus.COMPLETE][[id_col]] \
            .copy()
        nb_legs_by_trip_df["Nb. Legs"] = trips_legs_complete_series.map(len)

        return nb_legs_by_trip_df

    def get_trip_duration_stats(self) -> pd.DataFrame:
        trips_df = self.data_container.get_observations_table_df(
            self.__trips_table_name)
        id_col = self.data_container.get_columns("trips")["id"]
        status_col = self.data_container.get_columns("trips")["status"]
        time_col = self.data_container.get_columns("trips")["time"]

        trips_ready_complete_df = trips_df[trips_df[status_col].isin(
            [PassengerStatus.READY, PassengerStatus.COMPLETE])]
        trip_durations_df = trips_ready_complete_df.groupby(id_col).agg(
            {time_col: lambda x: max(x) - min(x)})

        return trip_durations_df

    def get_route_duration_stats(self) -> pd.DataFrame:
        vehicles_df = self.data_container.get_observations_table_df(
            self.__vehicles_table_name)
        id_col = self.data_container.get_columns("vehicles")["id"]
        status_col = self.data_container.get_columns("vehicles")["status"]
        time_col = self.data_container.get_columns("vehicles")["time"]

        vehicles_boarding_complete_df = vehicles_df[
            vehicles_df[status_col].isin([VehicleStatus.BOARDING,
                                          VehicleStatus.COMPLETE])]
        route_durations_df = vehicles_boarding_complete_df.groupby(id_col).agg(
            {time_col: lambda x: max(x) - min(x)})

        return route_durations_df

    def __load_config(self, config):
        if isinstance(config, str):
            config = DataAnalyzerConfig(config)
        elif not isinstance(config, DataAnalyzerConfig):
            config = DataAnalyzerConfig()

        self.__default_ghg_e = config.ghg_e
        self.__events_table_name = config.events_table
        self.__vehicles_table_name = config.vehicles_table
        self.__trips_table_name = config.trips_table

    def __generate_status_duration_stats(self, observations_df, table_name):
        id_col = self.data_container.get_columns(table_name)["id"]
        status_col = self.data_container.get_columns(table_name)["status"]
        time_col = self.data_container.get_columns(table_name)["time"]

        observations_grouped_by_id = observations_df.groupby(id_col)
        observations_df["duration"] = observations_grouped_by_id[time_col]. \
            transform(lambda s: s.shift(-1) - s)

        return observations_df.groupby(status_col, sort=False)["duration"]. \
            describe()

    def __get_nb_boardings_by_stop(self, trip_legs, nb_boardings_by_stop):
        for leg_pair in trip_legs:
            if leg_pair[0] not in nb_boardings_by_stop:
                nb_boardings_by_stop[leg_pair[0]] = 1
            else:
                nb_boardings_by_stop[leg_pair[0]] += 1

        return nb_boardings_by_stop

    def __get_nb_alightings_by_stop(self, trip_legs, nb_alightings_by_stop):
        for leg_pair in trip_legs:
            if leg_pair[1] not in nb_alightings_by_stop:
                nb_alightings_by_stop[leg_pair[1]] = 1
            else:
                nb_alightings_by_stop[leg_pair[1]] += 1

        return nb_alightings_by_stop
