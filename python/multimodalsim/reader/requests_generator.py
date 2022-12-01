import pandas as pd
import logging

from multimodalsim.config.config import RequestsGeneratorConfig

logger = logging.getLogger(__name__)


class RequestsGenerator:
    def __init__(self):
        pass

    def generate_requests(self):
        pass


class CAPRequestsGenerator(RequestsGenerator):

    def __init__(self, cap_file_path, stop_times_file_path,
                 config_file="config/cap_requests_generator.ini"):
        super().__init__()

        self.__cap_formatter = CAPFormatter(cap_file_path,
                                            stop_times_file_path)

        config = RequestsGeneratorConfig(config_file)
        self.__max_connection_time = config.max_connection_time
        self.__release_time_delta = config.release_time_delta
        self.__ready_time_delta = config.ready_time_delta
        self.__due_time_delta = config.due_time_delta

        self.__requests_df = None

    @property
    def requests_df(self):
        return self.__requests_df

    def generate_requests(self, max_connection_time=None,
                          release_time_delta=None, ready_time_delta=None,
                          due_time_delta=None):

        if max_connection_time is None:
            max_connection_time = self.__max_connection_time
        if release_time_delta is None:
            release_time_delta = self.__release_time_delta
        if ready_time_delta is None:
            ready_time_delta = self.__ready_time_delta
        if due_time_delta is None:
            due_time_delta = self.__due_time_delta

        formatted_cap_df = self.__cap_formatter.format_cap(max_connection_time)
        self.__extract_requests_from_cap(formatted_cap_df)
        self.__format_requests(release_time_delta, ready_time_delta,
                               due_time_delta)

        return self.__requests_df

    def save_to_csv(self, requests_file_path, requests_df=None):
        if requests_df is None and self.__requests_df is None:
            raise ValueError("Requests must be generated first!")

        if requests_df is None:
            requests_df = self.__requests_df

        requests_df.to_csv(requests_file_path, sep=";")

    def __extract_requests_from_cap(self, formatted_cap_df):
        cap_grouped_by_id_client = formatted_cap_df.groupby("CL_ID_CLIENT")

        all_group_requests_list = []
        boarding_columns = ['CL_ID_CLIENT', 'L_CHRONOBUS', 'S_H_DEP_REEL28']
        alighting_columns = ['D_CHRONOBUS_DESC', 'D_H_ARR_REEL28_DESC']
        for name, group in cap_grouped_by_id_client:
            boarding_df = group[group["boarding_type"] == "1ère montée"][
                boarding_columns].reset_index().drop("index", axis=1)
            alighting_df = group[(group["boarding_type_lead"] == "1ère montée")
                                 | (group["boarding_type_lead"].isna())][
                alighting_columns].reset_index().drop("index", axis=1)
            if len(boarding_df) == len(alighting_df):
                group_requests_df = pd.concat([boarding_df, alighting_df],
                                              axis=1)
                all_group_requests_list.append(group_requests_df)
            else:
                logger.warning(
                    "WARNING: len(boarding_df) ({}) != len(alighting_df) ({})"
                    .format(len(boarding_df), len(alighting_df)))

        self.__requests_df = pd.concat(all_group_requests_list)

        return self.__requests_df

    def __format_requests(self, release_time_delta, ready_time_delta,
                          due_time_delta):

        self.__requests_df["origin"] = self.__requests_df["L_CHRONOBUS"]
        self.__requests_df["destination"] = \
            self.__requests_df["D_CHRONOBUS_DESC"]
        self.__requests_df["nb_passengers"] = 1
        self.__requests_df["release_time"] = \
            self.__requests_df["S_H_DEP_REEL28"] - release_time_delta
        self.__requests_df["ready_time"] = self.__requests_df[
                                               "S_H_DEP_REEL28"] - ready_time_delta
        self.__requests_df["due_time"] = self.__requests_df[
                                             "D_H_ARR_REEL28_DESC"] + due_time_delta

        self.__requests_df = self.__requests_df.drop(
            ["L_CHRONOBUS", "S_H_DEP_REEL28", "D_CHRONOBUS_DESC",
             "D_H_ARR_REEL28_DESC"], axis=1)
        self.__requests_df["origin"] = self.__requests_df["origin"].apply(int)
        self.__requests_df["destination"] = \
            self.__requests_df["destination"].apply(int)
        self.__requests_df["release_time"] = \
            self.__requests_df["release_time"].apply(int)
        self.__requests_df["ready_time"] = \
            self.__requests_df["ready_time"].apply(int)
        self.__requests_df["due_time"] = \
            self.__requests_df["due_time"].apply(int)

        self.__requests_df.reset_index(drop=True, inplace=True)
        self.__requests_df.reset_index(inplace=True)

        self.__requests_df["ID"] = self.__requests_df["CL_ID_CLIENT"] + "_" \
                                   + self.__requests_df[
                                       "index"].apply(str)
        self.__requests_df.index = self.__requests_df["ID"]
        self.__requests_df.drop(["CL_ID_CLIENT", "index", "ID"], axis=1,
                                inplace=True)

        return self.__requests_df


class CAPFormatter:
    def __init__(self, cap_file_path, stop_times_file_path):
        self.__read_cap_csv(cap_file_path)
        self.__read_stop_times_csv(stop_times_file_path)

    @property
    def cap_df(self):
        return self.__cap_df

    def format_cap(self, max_connection_time):
        self.__preformat()
        self.__filter()
        self.__add_boarding_type(max_connection_time)

        return self.__cap_df

    def __read_cap_csv(self, cap_file_path):
        self.__cap_df = pd.read_csv(cap_file_path, delimiter=";")

    def __read_stop_times_csv(self, stop_times_file_path):
        self.__stop_times_df = pd.read_csv(stop_times_file_path,
                                           dtype={"stop_id": str})

    def __preformat(self):
        cap_columns = ["L_CHRONOBUS", "L_CHRONOBUS_DESCRIPTION",
                       "D_CHRONOBUS_DESC", "D_CHRONOBUS_DESCRIPTION_DESC",
                       "S_H_DEP_REEL28_DT", "S_H_DEP_REEL28",
                       "D_H_ARR_REEL28_DESC_DT", "D_H_ARR_REEL28_DESC",
                       "C_TYPE_VALIDATION", "CL_ID_CLIENT", "L_LAT_ARRET",
                       "L_LON_ARRET", "D_LAT_STOP_DESC", "D_LON_STOP_DESC",
                       "S_VEHJOBID_IDJOURNALIER"]
        self.__cap_df = self.__cap_df.sort_values(
            ["CL_ID_CLIENT", "S_H_DEP_REEL28"])[cap_columns].dropna()
        self.__cap_df = self.__cap_df.astype(
            {"L_CHRONOBUS": int, "D_CHRONOBUS_DESC": int,
             "S_VEHJOBID_IDJOURNALIER": int})
        self.__cap_df = self.__cap_df.astype(
            {"L_CHRONOBUS": str, "D_CHRONOBUS_DESC": str})

        return self.__cap_df

    def __filter(self):
        stop_times_grouped_by_id = self.__stop_times_df.groupby("trip_id")
        stops_by_trip_series = stop_times_grouped_by_id["stop_id"].apply(list)
        cap_with_stops_list_df = self.__cap_df.merge(
            stops_by_trip_series, left_on="S_VEHJOBID_IDJOURNALIER",
            right_index=True)

        cap_with_stops_list_df["trip_exists"] = cap_with_stops_list_df.apply(
            lambda x: x["L_CHRONOBUS"] in x["stop_id"] and x[
                "D_CHRONOBUS_DESC"] in x["stop_id"], axis=1)

        self.__cap_df = cap_with_stops_list_df[
            cap_with_stops_list_df["trip_exists"]]

        return self.__cap_df

    def __add_boarding_type(self, max_connection_time):
        cap_grouped_by_id_client = self.__cap_df.groupby("CL_ID_CLIENT")

        self.__cap_df["D_H_ARR_REEL28_DESC_lag"] = cap_grouped_by_id_client[
            "D_H_ARR_REEL28_DESC"].shift(1)
        self.__cap_df["arr_dep_diff"] = self.__cap_df["S_H_DEP_REEL28"] - \
                                        self.__cap_df[
                                            "D_H_ARR_REEL28_DESC_lag"]
        self.__cap_df["boarding_type"] = self.__cap_df.apply(
            lambda x: x["C_TYPE_VALIDATION"]
            if x["arr_dep_diff"] < max_connection_time
            else "1ère montée", axis=1)
        self.__cap_df["boarding_type_lead"] = cap_grouped_by_id_client[
            "boarding_type"].shift(-1)

        self.__cap_df["L_CHRONOBUS"] = self.__cap_df["L_CHRONOBUS"].apply(
            int)
        self.__cap_df["D_CHRONOBUS_DESC"] = self.__cap_df[
            "D_CHRONOBUS_DESC"].apply(int)

        return self.__cap_df
