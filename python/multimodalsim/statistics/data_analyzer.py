import pandas as pd

from multimodalsim.simulator.status import PassengersStatus, VehicleStatus


class DataAnalyzer:

    def __init__(self, data_container=None):
        self.__data_container = data_container

        pd.set_option('display.max_rows', 50)
        pd.set_option('display.max_columns', 50)

    @property
    def data_container(self):
        return self.__data_container

    @data_container.setter
    def data_container(self, data_container):
        self.__data_container = data_container

    def get_description(self, table_name):
        observations_df = self.data_container \
            .get_observations_table_df(table_name)

        return observations_df.describe(datetime_is_numeric=True)


class FixedLineDataAnalyzer(DataAnalyzer):

    def __init__(self, data_container=None, events_table_name="events",
                 vehicles_table_name="vehicles", trips_table_name="trips"):
        super().__init__(data_container)

        self.__events_df = \
            self.data_container.get_observations_table_df(events_table_name)
        self.__vehicles_df = \
            self.data_container.get_observations_table_df(vehicles_table_name)
        self.__trips_df = \
            self.data_container.get_observations_table_df(trips_table_name)

    @property
    def nb_events(self):
        return len(self.__events_df)

    @property
    def nb_event_types(self):
        name_col = self.data_container.get_columns("events")["name"]
        return len(self.__events_df.groupby(name_col))

    @property
    def nb_events_by_type(self):
        name_col = self.data_container.get_columns("events")["name"]
        return self.__events_df[name_col].value_counts().sort_index()

    @property
    def nb_trips(self):
        id_col = self.data_container.get_columns("trips")["id"]
        return len(self.__trips_df.groupby(id_col))

    @property
    def nb_vehicles(self):
        id_col = self.data_container.get_columns("vehicles")["id"]
        return len(self.__vehicles_df.groupby(id_col))

    def get_vehicle_status_duration_statistics(self):
        return self.__generate_status_duration_stats(self.__vehicles_df,
                                                     "vehicles")

    def get_trip_status_duration_statistics(self):
        return self.__generate_status_duration_stats(self.__trips_df, "trips")

    def get_boardings_alightings_stats(self):
        status_col = self.data_container.get_columns("trips")["status"]
        previous_legs_col = self.data_container.get_columns("trips")[
            "previous_legs"]
        current_leg_col = self.data_container.get_columns("trips")[
            "current_leg"]

        trips_complete_series = self.__trips_df[self.__trips_df[status_col]
                                                == PassengersStatus.COMPLETE]

        trips_legs_complete_series = trips_complete_series.apply(
            lambda x: x[previous_legs_col] + [x[current_leg_col]], axis=1)

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

    def get_max_load_by_vehicle(self):
        onboard_legs_col = self.data_container.get_columns("vehicles")[
            "onboard_legs"]
        id_col = self.data_container.get_columns("vehicles")["id"]

        vehicles_load_df = self.__vehicles_df.copy()
        vehicles_load_df["max load"] = vehicles_load_df[onboard_legs_col]. \
            apply(len)
        vehicles_max_load_df = vehicles_load_df.groupby(id_col). \
            agg({"max load": max})
        return vehicles_max_load_df

    def get_nb_legs_by_trip_stats(self):
        id_col = self.data_container.get_columns("trips")["id"]
        status_col = self.data_container.get_columns("trips")["status"]
        previous_legs_col = self.data_container.get_columns("trips")[
            "previous_legs"]
        current_leg_col = self.data_container.get_columns("trips")[
            "current_leg"]

        trips_complete_series = self.__trips_df[self.__trips_df[status_col]
                                                == VehicleStatus.COMPLETE]
        trips_legs_complete_series = trips_complete_series.apply(
            lambda x: x[previous_legs_col] + [x[current_leg_col]], axis=1)

        nb_legs_by_trip_df = self.__trips_df[
            self.__trips_df[status_col] == VehicleStatus.COMPLETE][[id_col]] \
            .copy()
        nb_legs_by_trip_df["Nb. Legs"] = trips_legs_complete_series.map(len)

        return nb_legs_by_trip_df

    def get_trip_duration_stats(self):
        id_col = self.data_container.get_columns("trips")["id"]
        status_col = self.data_container.get_columns("trips")["status"]
        time_col = self.data_container.get_columns("trips")["time"]

        trips_ready_complete_df = self.__trips_df[
            self.__trips_df[status_col].isin([PassengersStatus.READY,
                                              PassengersStatus.COMPLETE])]
        trip_durations_df = trips_ready_complete_df.groupby(id_col).agg(
            {time_col: lambda x: max(x) - min(x)})

        return trip_durations_df

    def get_route_duration_stats(self):
        id_col = self.data_container.get_columns("vehicles")["id"]
        status_col = self.data_container.get_columns("vehicles")["status"]
        time_col = self.data_container.get_columns("vehicles")["time"]

        vehicles_boarding_complete_df = self.__vehicles_df[
            self.__vehicles_df[status_col].isin([VehicleStatus.BOARDING,
                                               VehicleStatus.COMPLETE])]
        route_durations_df = vehicles_boarding_complete_df.groupby(id_col).agg(
            {time_col: lambda x: max(x) - min(x)})

        return route_durations_df

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
