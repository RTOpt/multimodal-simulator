from multimodalsim.config.config import Config

import os


class GTFSGeneratorConfig(Config):
    def __init__(self,
                 config_file=os.path.join(os.path.dirname(__file__),
                                          "ini/gtfs_generator.ini")):
        super().__init__(config_file)

    @property
    def trip_id_col(self):
        return self._config_parser["input_columns"]["trip_id"]

    @property
    def arrival_time_col(self):
        return self._config_parser["input_columns"]["arrival_time"]

    @property
    def departure_time_col(self):
        return self._config_parser["input_columns"]["departure_time"]

    @property
    def stop_id_col(self):
        return self._config_parser["input_columns"]["stop_id"]

    @property
    def stop_sequence_col(self):
        return self._config_parser["input_columns"]["stop_sequence"]

    @property
    def line_col(self):
        return self._config_parser["input_columns"]["line"]

    @property
    def direction_col(self):
        return self._config_parser["input_columns"]["direction"]

    @property
    def service_id_col(self):
        return self._config_parser["input_columns"]["service_id"]

    @property
    def date_col(self):
        return self._config_parser["input_columns"]["date"]

    @property
    def shape_dist_traveled_col(self):
        return self._config_parser["input_columns"]["shape_dist_traveled"]

    @property
    def stop_name_col(self):
        return self._config_parser["input_columns"]["stop_name"]

    @property
    def stop_lon_col(self):
        return self._config_parser["input_columns"]["stop_lon"]

    @property
    def stop_lat_col(self):
        return self._config_parser["input_columns"]["stop_lat"]


