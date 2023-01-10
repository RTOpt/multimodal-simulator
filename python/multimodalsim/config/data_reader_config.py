from multimodalsim.config.config import Config

import os


class DataReaderConfig(Config):
    def __init__(self,
                 config_file=os.path.join(os.path.dirname(__file__),
                                          "ini/gtfs_data_reader.ini")):
        super().__init__(config_file)

    def get_trips_columns(self):
        trips_columns = {
            "id": int(self._config_parser["trips"]["id"]),
            "origin": int(self._config_parser["trips"]["origin"]),
            "destination": int(self._config_parser["trips"]["destination"]),
            "nb_passengers": int(
                self._config_parser["trips"]["nb_passengers"]),
            "release_time": int(self._config_parser["trips"]["release_time"]),
            "ready_time": int(self._config_parser["trips"]["ready_time"]),
            "due_time": int(self._config_parser["trips"]["due_time"]),
            "legs": int(self._config_parser["trips"]["legs"])
        }

        return trips_columns
