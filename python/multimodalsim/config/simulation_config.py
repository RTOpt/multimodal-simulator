from multimodalsim.config.config import Config

import os


class SimulationConfig(Config):
    def __init__(
            self,
            config_file: str = os.path.join(os.path.dirname(__file__),
                                            "ini/simulation.ini")) -> None:
        super().__init__(config_file)

    @property
    def speed(self) -> float:
        if len(self._config_parser["time_sync_event"]["speed"]) == 0:
            speed = None
        else:
            speed = float(self._config_parser["time_sync_event"]["speed"])
        return speed

    @property
    def time_step(self) -> float:
        if len(self._config_parser["time_sync_event"]["time_step"]) == 0:
            time_step = None
        else:
            time_step = float(self._config_parser[
                                "time_sync_event"]["time_step"])
        return time_step

    @property
    def update_position_time_step(self) -> float:
        if len(self._config_parser["update_position_event"]["time_step"]) == 0:
            time_step = None
        else:
            time_step = float(self._config_parser[
                                "update_position_event"]["time_step"])
        return time_step

    @property
    def max_time(self) -> float:
        if len(self._config_parser["general"]["max_time"]) == 0:
            max_time = None
        else:
            max_time = float(self._config_parser["general"]["max_time"])

        return max_time
