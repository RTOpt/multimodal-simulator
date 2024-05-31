import pandas as pd
import os
import logging

from multimodalsim.config.gtfs_generator_config import GTFSGeneratorConfig

logger = logging.getLogger(__name__)

class GTFSGenerator:
###This class reads files containing the passage_arret data from the STL and generates the corresponding GTFS-type files.
### Input files are named Donnees_PASSAGE_ARRET_VLV_2019-11-01_2019-11-30.scv.
### Output files for each day are saved in a folder named after the date, in the gtfs_folder folder.
    def __init__(self, config=None):
        config = GTFSGeneratorConfig() if config is None else config
        self.__load_config(config)

        self.__passage_arret_file_path_list = None
        self.__stop_times_df = None
        self.__stops_df = None

    def build_calendar_dates(self, passage_arret_file_path_list,
                             gtfs_folder=None):

        self.__passage_arret_file_path_list = passage_arret_file_path_list

        passage_arret_df = self.__get_passage_arret_df()

        calendar_dates_columns = [self.__service_id_col, self.__date_col]
        calendar_dates_df = passage_arret_df.loc[:, calendar_dates_columns] \
            .dropna()

        calendar_dates_df.loc[:, "service_id"] = \
            calendar_dates_df[self.__service_id_col]
        calendar_dates_df.loc[:, "date"] = \
            calendar_dates_df[self.__date_col].apply(
                lambda x: "".join(x.split(" ")[0].split("-")))
        calendar_dates_df["exception_type"] = 1
        calendar_dates_df.drop_duplicates(inplace=True)
        calendar_dates_df = calendar_dates_df[["service_id", "date",
                                               "exception_type",
                                               self.__date_col]]

        if gtfs_folder is not None:
            self.__save_to_file(calendar_dates_df, "calendar_dates.txt",
                                gtfs_folder)

    def build_trips(self, passage_arret_file_path_list, gtfs_folder=None):

        self.__passage_arret_file_path_list = passage_arret_file_path_list

        passage_arret_df = self.__get_passage_arret_df()

        trips_columns = [self.__line_col, self.__direction_col,
                         self.__service_id_col,
                         self.__trip_id_col, self.__date_col]

        trips_df = passage_arret_df.loc[:, trips_columns].dropna()
        trips_df.drop_duplicates(inplace=True)

        trips_df.loc[:, "route_id"] = trips_df.loc[:, self.__line_col] \
                                      + trips_df.loc[:, self.__direction_col]
        trips_df.loc[:, "service_id"] = trips_df.loc[:, self.__service_id_col]
        trips_df.loc[:, "trip_id"] = trips_df.loc[:, self.__trip_id_col]
        trips_df.loc[:, "shape_id"] = trips_df.loc[:, self.__line_col] \
                                      + trips_df.loc[:, self.__direction_col]
        trips_df.loc[:, "trip_short_name"] = trips_df.loc[:, self.__line_col]

        columns_to_keep = ["route_id", "service_id", "trip_id", "shape_id",
                           "trip_short_name", self.__date_col]
        trips_df = trips_df[columns_to_keep]
        trips_df.sort_values(columns_to_keep, inplace=True)

        if gtfs_folder is not None:
            self.__save_to_file(trips_df, "trips.txt", gtfs_folder)

        return trips_df

    def build_stops(self, passage_arret_file_path_list, gtfs_folder=None):

        self.__passage_arret_file_path_list = passage_arret_file_path_list

        passage_arret_df = self.__get_passage_arret_df()

        stops_columns = [self.__date_col, self.__stop_id_col,
                         self.__stop_name_col, self.__stop_lon_col,
                         self.__stop_lat_col]

        stops_df = passage_arret_df[stops_columns].groupby(
            [self.__date_col, self.__stop_id_col]).first().reset_index()
        stops_df.rename({self.__stop_id_col: "stop_id",
                         self.__stop_name_col: "stop_name",
                         self.__stop_lon_col: "stop_lon",
                         self.__stop_lat_col: "stop_lat"}, axis=1,
                        inplace=True)

        if gtfs_folder is not None:
            self.__save_to_file(stops_df, "stops.txt",
                                gtfs_folder)

        return stops_df

    def build_stop_times(self, passage_arret_file_path_list, gtfs_folder=None,
                         shape_dist_traveled=False):

        self.__passage_arret_file_path_list = passage_arret_file_path_list

        passage_arret_df = self.__get_passage_arret_df()

        stop_times_columns = [self.__date_col, self.__line_col,
                              self.__direction_col, self.__trip_id_col,
                              self.__arrival_time_col,
                              self.__departure_time_col, self.__stop_id_col,
                              self.__stop_sequence_col,
                              self.__shape_dist_traveled_col]

        self.__stop_times_df = passage_arret_df[
            stop_times_columns].sort_values(
            [self.__date_col, self.__trip_id_col,
             self.__stop_sequence_col]).dropna()
        stop_times_with_orig_time_df = \
            self.__get_stop_times_with_orig_time_df()

        trip_id_set = self.__get_trip_id_set()

        stop_times_with_orig_time_filtered_df = stop_times_with_orig_time_df[
            stop_times_with_orig_time_df[self.__trip_id_col].isin(trip_id_set)]

        full_stop_times_df = self.__get_full_stop_times_df(
            stop_times_with_orig_time_filtered_df)

        gtfs_stop_times_df = self.__get_stop_times_df(full_stop_times_df,
                                                      shape_dist_traveled)

        date_by_trip_id_series = \
            self.__stop_times_df.groupby(self.__trip_id_col)[
                self.__date_col].apply(
                lambda x: list(set(x))[0])

        stop_times_with_date_df = gtfs_stop_times_df.merge(
            date_by_trip_id_series, left_on="trip_id", right_index=True)

        stop_times_with_date_df["arrival_time"] = stop_times_with_date_df[
            "arrival_time"].dropna()
        stop_times_with_date_df["departure_time"] = stop_times_with_date_df[
            "departure_time"].dropna()

        stop_times_with_date_df["arrival_time"] = \
            stop_times_with_date_df["arrival_time"].astype(int)
        stop_times_with_date_df["departure_time"] = \
            stop_times_with_date_df["departure_time"].astype(int)

        stop_times_with_date_df = \
            self.__correct_stop_times_df(stop_times_with_date_df)

        if gtfs_folder is not None:
            self.__save_to_file(stop_times_with_date_df, "stop_times.txt",
                                gtfs_folder)

        return stop_times_with_date_df
    
    def build_stop_times_upgrade(self, passage_arret_file_path_list, gtfs_folder=None,
                         shape_dist_traveled=True):

        self.__passage_arret_file_path_list = passage_arret_file_path_list

        passage_arret_df = self.__get_passage_arret_upgrade_df()

        stop_times_columns = [self.__date_col, self.__line_col,
                              self.__direction_col, self.__trip_id_col,
                              self.__arrival_time_col,
                              self.__departure_time_col, self.__stop_id_col,
                              self.__stop_sequence_col,
                              self.__shape_dist_traveled_col,
                              self.__planned_arrival_time_col,
                              self.__planned_departure_time_from_origin_col]

        self.__stop_times_df = passage_arret_df[
            stop_times_columns].sort_values(
            [self.__date_col, self.__trip_id_col,
             self.__stop_sequence_col]).dropna()
        stop_times_with_orig_time_df = \
            self.__get_stop_times_with_orig_time_df()

        trip_id_set = self.__get_trip_id_set()

        stop_times_with_orig_time_filtered_df = stop_times_with_orig_time_df[
            stop_times_with_orig_time_df[self.__trip_id_col].isin(trip_id_set)]

        full_stop_times_df = self.__get_full_stop_times_df(
            stop_times_with_orig_time_filtered_df)

        gtfs_stop_times_df = self.__get_stop_times_df(full_stop_times_df,
                                                      shape_dist_traveled=True)

        date_by_trip_id_series = \
            self.__stop_times_df.groupby(self.__trip_id_col)[
                self.__date_col].apply(
                lambda x: list(set(x))[0])

        stop_times_with_date_df = gtfs_stop_times_df.merge(
            date_by_trip_id_series, left_on="trip_id", right_index=True)

        stop_times_with_date_df["arrival_time"] = stop_times_with_date_df[
            "arrival_time"].dropna()
        stop_times_with_date_df["departure_time"] = stop_times_with_date_df[
            "departure_time"].dropna()

        stop_times_with_date_df["arrival_time"] = \
            stop_times_with_date_df["arrival_time"].astype(int)
        stop_times_with_date_df["departure_time"] = \
            stop_times_with_date_df["departure_time"].astype(int)
        stop_times_with_date_df["planned_arrival_time"] = \
            stop_times_with_date_df["planned_arrival_time"].astype(int)
        stop_times_with_date_df["planned_departure_time_from_origin"] = \
            stop_times_with_date_df["planned_departure_time_from_origin"].astype(int)

        stop_times_with_date_df = \
            self.__correct_stop_times_df(stop_times_with_date_df)

        if gtfs_folder is not None:
            self.__save_to_file(stop_times_with_date_df, "stop_times_upgrade.txt",
                                gtfs_folder, upgrade=True)

        return stop_times_with_date_df

    def __load_config(self, config):
        self.__trip_id_col = config.trip_id_col
        self.__arrival_time_col = config.arrival_time_col
        self.__departure_time_col = config.departure_time_col
        self.__stop_id_col = config.stop_id_col
        self.__stop_sequence_col = config.stop_sequence_col
        self.__line_col = config.line_col
        self.__direction_col = config.direction_col
        self.__service_id_col = config.service_id_col
        self.__date_col = config.date_col
        self.__shape_dist_traveled_col = config.shape_dist_traveled_col
        self.__stop_name_col = config.stop_name_col
        self.__stop_lon_col = config.stop_lon_col
        self.__stop_lat_col = config.stop_lat_col
        self.__stop_passenger_count_col = config.stop_passenger_count_col
        self.__nb_boarding_col = config.nb_boarding_col
        self.__nb_alighting_col = config.nb_alighting_col
        self.__planned_arrival_time_col = config.planned_arrival_time_col
        self.__planned_departure_time_from_origin_col = config.planned_departure_time_from_origin_col

    def __save_to_file(self, gtfs_df, file_name, gtfs_folder, upgrade = False):
        if not os.path.exists(gtfs_folder):
            os.makedirs(gtfs_folder)

        # gtfs_df = gtfs_df.dropna()

        dates_list = gtfs_df[self.__date_col].unique()
        for date in dates_list:
            trips_day_df = gtfs_df[
                gtfs_df[self.__date_col] == date].drop(self.__date_col, axis=1)
            gtfs_day_folder = gtfs_folder + date.split(" ")[0] + "/"
            if not os.path.exists(gtfs_day_folder):
                os.makedirs(gtfs_day_folder)

            trips_day_df.to_csv(gtfs_day_folder + file_name, index=None)

    def __get_passage_arret_df(self):

        columns_type_dict = {
            self.__trip_id_col: str,
            self.__direction_col: str,
            self.__line_col: str,
            self.__service_id_col: str,
            self.__arrival_time_col: float,
            self.__departure_time_col: float,
            self.__stop_id_col: str,
            self.__stop_sequence_col: int,
            self.__shape_dist_traveled_col: float,
            self.__date_col: str,
            self.__stop_name_col: str,
            self.__stop_lon_col: float,
            self.__stop_lat_col: float}

        passage_arret_df_list = []
        for passage_arret_file_path in self.__passage_arret_file_path_list:
            passage_arret_df_temp = pd.read_csv(passage_arret_file_path,
                                                usecols=columns_type_dict.keys(),
                                                delimiter=",",
                                                dtype=columns_type_dict)
            passage_arret_df_list.append(passage_arret_df_temp)
        passage_arret_df = pd.concat(passage_arret_df_list).reset_index(
            drop=True)

        return passage_arret_df
    
    def __get_passage_arret_upgrade_df(self):

        columns_type_dict = {
            self.__trip_id_col: str,
            self.__direction_col: str,
            self.__line_col: str,
            self.__service_id_col: str,
            self.__arrival_time_col: float,
            self.__departure_time_col: float,
            self.__stop_id_col: str,
            self.__stop_sequence_col: int,
            self.__shape_dist_traveled_col: float,
            self.__date_col: str,
            self.__stop_name_col: str,
            self.__stop_lon_col: float,
            self.__stop_lat_col: float,
            self.__planned_arrival_time_col: int,
            self.__planned_departure_time_from_origin_col: int
            }
        passage_arret_df_list = []
        for passage_arret_file_path in self.__passage_arret_file_path_list:
            passage_arret_df_temp = pd.read_csv(passage_arret_file_path,
                                                usecols=columns_type_dict.keys(),
                                                delimiter=",",
                                                dtype=columns_type_dict)
            passage_arret_df_list.append(passage_arret_df_temp)
        passage_arret_df = pd.concat(passage_arret_df_list).reset_index(
            drop=True)

        return passage_arret_df

    def __get_stop_times_with_orig_time_df(self):
        stop_times_seq_min_df = self.__stop_times_df.loc[
            self.__stop_times_df.groupby(self.__trip_id_col)[
                self.__stop_sequence_col].idxmin()]
        stop_times_seq0_df = stop_times_seq_min_df[
            stop_times_seq_min_df[self.__stop_sequence_col] == 0]
        time_seq0_df = stop_times_seq0_df[
            [self.__trip_id_col, self.__arrival_time_col,
             self.__departure_time_col]].rename(
            {self.__arrival_time_col: "arr_orig",
             self.__departure_time_col: "dep_orig"}, axis=1)

        stop_times_with_orig_time_df = self.__stop_times_df.merge(
            time_seq0_df, left_on=self.__trip_id_col,
            right_on=self.__trip_id_col, how="left")
        stop_times_with_orig_time_df["arr_time_from_orig"] = \
            stop_times_with_orig_time_df[self.__arrival_time_col] - \
            stop_times_with_orig_time_df["arr_orig"]
        stop_times_with_orig_time_df["dep_time_from_orig"] = \
            stop_times_with_orig_time_df[self.__departure_time_col] - \
            stop_times_with_orig_time_df["dep_orig"]
        stop_times_with_orig_time_df.dropna(inplace=True)

        return stop_times_with_orig_time_df

    def __get_trip_id_set(self):
        stop_times_grouped_by_line_seq = self.__stop_times_df.groupby(
            [self.__line_col, self.__direction_col, self.__stop_sequence_col])
        nb_chronobus_by_stop = stop_times_grouped_by_line_seq[
            self.__stop_id_col].apply(lambda x: len(set(x)))

        stop_times_grouped_by_line_seq_chronobus = \
            self.__stop_times_df.groupby([self.__line_col,
                                          self.__direction_col,
                                          self.__stop_sequence_col,
                                          self.__stop_id_col])
        trip_id_by_stop = stop_times_grouped_by_line_seq_chronobus[
            self.__trip_id_col].apply(set)

        trip_id_set = set().union(
            *list(trip_id_by_stop[nb_chronobus_by_stop == 1]))

        return trip_id_set

    def __get_full_stop_times_df(self, stop_times_with_orig_time_filtered_df):
        stop_times_orig_time_grouped_by_line_seq = \
            stop_times_with_orig_time_filtered_df.groupby(
                [self.__line_col, self.__direction_col,
                 self.__stop_sequence_col])
        bus_id_by_line_seq_series = stop_times_orig_time_grouped_by_line_seq[
            self.__stop_id_col].first()
        mean_shape_dist_traveled_by_line_seq_series = \
            stop_times_orig_time_grouped_by_line_seq[
                self.__shape_dist_traveled_col].mean()
        arr_time_from_orig_by_line_seq_series = \
            stop_times_orig_time_grouped_by_line_seq[
                "arr_time_from_orig"].mean()
        dep_time_from_orig_by_line_seq_series = \
            stop_times_orig_time_grouped_by_line_seq[
                "dep_time_from_orig"].mean()

        line_seq_df = pd.DataFrame(
            {"stop_id": bus_id_by_line_seq_series,
             "mean_shape_dist_traveled":
                 mean_shape_dist_traveled_by_line_seq_series,
             "arr_time_from_orig":
                 arr_time_from_orig_by_line_seq_series,
             "dep_time_from_orig":
                 dep_time_from_orig_by_line_seq_series})
        trip_id_by_line_series = \
            stop_times_with_orig_time_filtered_df.groupby(
                [self.__line_col, self.__direction_col])[
                self.__trip_id_col].apply(
                lambda x: list(set(x)))
        all_trip_id_by_line_series = trip_id_by_line_series.explode()
        line_seq_with_trip_id_df = line_seq_df.merge(
            all_trip_id_by_line_series,
            left_on=[self.__line_col, self.__direction_col], right_index=True)
        line_job_seq_df = line_seq_with_trip_id_df.reset_index().groupby(
            [self.__line_col, self.__direction_col, self.__trip_id_col,
             self.__stop_sequence_col]).first()
        full_stop_times_df = line_job_seq_df.merge(
            self.__stop_times_df, left_index=True,
            right_on=[self.__line_col, self.__direction_col,
                      self.__trip_id_col, self.__stop_sequence_col],
            how="left")

        full_stop_times_seq0_df = full_stop_times_df[
            full_stop_times_df[self.__stop_sequence_col] == 0]
        arr_dep_trip_id_df = full_stop_times_seq0_df[
            [self.__trip_id_col, self.__arrival_time_col,
             self.__departure_time_col]].rename(
            {self.__arrival_time_col: "arr_orig",
             self.__departure_time_col: "dep_orig"},
            axis=1)

        full_stop_times_df = full_stop_times_df.merge(
            arr_dep_trip_id_df, left_on=self.__trip_id_col,
            right_on=self.__trip_id_col)

        return full_stop_times_df

    def __get_stop_times_df(self, full_stop_times_df, shape_dist_traveled):
        full_stop_times_df["trip_id"] = \
            full_stop_times_df[self.__trip_id_col]
        full_stop_times_df["arrival_time"] = full_stop_times_df.apply(
            lambda x: x[self.__arrival_time_col] if not pd.isnull(
                x[self.__arrival_time_col])
            else x["arr_time_from_orig"] + x["arr_orig"], axis=1)
        if shape_dist_traveled:
            full_stop_times_df["planned_arrival_time"] = full_stop_times_df.apply(
                lambda x: x[self.__planned_arrival_time_col] if not pd.isnull(
                    x[self.__planned_arrival_time_col])
                else x["arr_time_from_orig"] + x["arr_orig"], axis=1)
            full_stop_times_df["planned_departure_time_from_origin"] = full_stop_times_df.apply(
                lambda x: x[self.__planned_departure_time_from_origin_col] if not pd.isnull(
                    x[self.__planned_departure_time_from_origin_col])
                else x["arr_orig"], axis=1)
        full_stop_times_df["departure_time"] = full_stop_times_df.apply(
            lambda x: x[self.__departure_time_col] if not pd.isnull(
                x[self.__departure_time_col])
            else x["dep_time_from_orig"] + x["dep_orig"], axis=1)
        full_stop_times_df["shape_dist_traveled"] = full_stop_times_df.apply(
            lambda x: x[self.__shape_dist_traveled_col] if not pd.isnull(
                x[self.__shape_dist_traveled_col])
            else x["mean_shape_dist_traveled"], axis=1)

        # Correct departure_time in case the "travel time" is nonpositive.
        full_stop_times_df["arrival_time_lead"] = \
            full_stop_times_df.groupby(["trip_id"])["arrival_time"].shift(-1)
        full_stop_times_df["travel_time"] = \
            full_stop_times_df["arrival_time_lead"] \
            - full_stop_times_df["departure_time"]
        full_stop_times_df["departure_time"] = full_stop_times_df.apply(
            lambda x: x["departure_time"] if x["travel_time"] > 0
            else x["arrival_time"], axis=1)

        # Keep only stop_times for which travel time is positive.
        full_stop_times_df["arrival_time_lead"] = \
            full_stop_times_df.groupby(["trip_id"])["arrival_time"].shift(-1)
        full_stop_times_df["travel_time"] = \
            full_stop_times_df["arrival_time_lead"] \
            - full_stop_times_df["departure_time"]
        full_stop_times_df = full_stop_times_df[full_stop_times_df["travel_time"] > 0]

        #
        full_stop_times_grouped_by_voy_id = \
            full_stop_times_df.groupby("trip_id")
        full_stop_times_df["prev_arrival_times"] = \
            full_stop_times_grouped_by_voy_id["arrival_time"].transform(
                lambda x: [list(x.iloc[:e]) for e, i in enumerate(x)])
        full_stop_times_df["prev_departure_times"] = \
            full_stop_times_grouped_by_voy_id["departure_time"].transform(
                lambda x: [list(x.iloc[:e]) for e, i in enumerate(x)])
        full_stop_times_df["max_prev_arrival_times"] = full_stop_times_df[
            "prev_arrival_times"].apply(
            lambda x: max(x) if len(x) > 0 else None)
        full_stop_times_df["max_prev_departure_times"] = full_stop_times_df[
            "prev_departure_times"].apply(
            lambda x: max(x) if len(x) > 0 else None)

        full_stop_times_df = full_stop_times_df[
            full_stop_times_df["arrival_time"] >= full_stop_times_df[
                "max_prev_arrival_times"]]
        full_stop_times_df = full_stop_times_df[
            full_stop_times_df["departure_time"] >= full_stop_times_df[
                "max_prev_departure_times"]]

        full_stop_times_df["stop_sequence"] = full_stop_times_df[
            self.__stop_sequence_col]
        full_stop_times_df["pickup_type"] = 0
        full_stop_times_df["drop_off_type"] = 0

        gtfs_columns = ["trip_id", "arrival_time", "departure_time", "stop_id",
                        "stop_sequence", "pickup_type", "drop_off_type"]
        if shape_dist_traveled:
            gtfs_columns.append("shape_dist_traveled")
            gtfs_columns.append("planned_arrival_time")
            gtfs_columns.append("planned_departure_time_from_origin")

        stop_times_all_dates_df = full_stop_times_df[gtfs_columns]

        return stop_times_all_dates_df

    def __correct_stop_times_df(self, stop_times_df):

        # departure_time should always be greater than arrival_time
        stop_times_df["departure_time"] = stop_times_df.apply(
            lambda x: x["departure_time"] if x["departure_time"] >= x[
                "arrival_time"] else x["arrival_time"], axis=1)

        # arrival_time of next stop should always be greater than
        # departure_time of current stop
        stop_times_df["arrival_time_lead"] = stop_times_df.groupby(
            [self.__date_col, "trip_id"])["arrival_time"].shift(-1)
        stop_times_df["departure_time"] = stop_times_df.apply(
            lambda x: x["departure_time"] if x["arrival_time_lead"] >= x[
                "departure_time"] else x["arrival_time"], axis=1)

        # Ignore remaining stops for which arrival_time of next stop is lower
        # than departure_time of current stop. (May happen if arrival_time of
        # current stop is greater than arrival time of next stop)
        stop_times_df = stop_times_df[
            stop_times_df["arrival_time_lead"] >= stop_times_df[
                "departure_time"]]

        stop_times_df = stop_times_df.drop("arrival_time_lead", axis=1)

        return stop_times_df
