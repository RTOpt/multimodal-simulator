from multimodalsim.config.config import Config

import os


class SimulationConfig(Config):
    def __init__(
            self,
            config_file: str = os.path.join(os.path.dirname(__file__),
                                            "ini/simulation.ini")) -> None:
        super().__init__(config_file)

        self.__init_time_step()
        self.__init_speed()
        self.__init_update_position_time_step()
        self.__init_max_time()

    @property
    def time_step(self) -> float:
        return self.__time_step

    @time_step.setter
    def time_step(self, time_step: float) -> None:
        self.__time_step = time_step

    @property
    def speed(self) -> float:
        return self.__speed

    @speed.setter
    def speed(self, speed: float) -> None:
        self.__speed = speed

    @property
    def update_position_time_step(self) -> float:
        return self.__update_position_time_step

    @update_position_time_step.setter
    def update_position_time_step(self,
                                  update_position_time_step: float) -> None:
        self.__update_position_time_step = update_position_time_step

    @property
    def max_time(self) -> float:
        return self.__max_time

    @max_time.setter
    def max_time(self, max_time: float) -> None:
        self.__max_time = max_time

    def __init_time_step(self):
        if len(self._config_parser["time_sync_event"]["time_step"]) == 0:
            self.__time_step = None
        else:
            self.__time_step = float(self._config_parser[
                                         "time_sync_event"]["time_step"])

    def __init_speed(self):
        if len(self._config_parser["time_sync_event"]["speed"]) == 0:
            self.__speed = None
        else:
            self.__speed = float(
                self._config_parser["time_sync_event"]["speed"])

    def __init_update_position_time_step(self):
        if len(self._config_parser["update_position_event"]["time_step"]) \
                == 0:
            self.__update_position_time_step = None
        else:
            self.__update_position_time_step = \
                float(self._config_parser["update_position_event"][
                          "time_step"])

    def __init_max_time(self):
        if len(self._config_parser["general"]["max_time"]) == 0:
            self.__max_time = None
        else:
            self.__max_time = \
                float(self._config_parser["general"]["max_time"])
