from multimodalsim.config.config import Config

import os


class StateStorageConfig(Config):

    SAVING = True
    SAVING_STEP_DEFAULT = 5
    OVERWRITE_FILE_DEFAULT = True
    FILENAME_DEFAULT = "state"

    def __init__(
            self,
            config_file: str = os.path.join(os.path.dirname(__file__),
                                            "ini/state_storage.ini")) -> None:
        super().__init__(config_file)

        self.__init_saving_time_step()

        self.__init_overwrite_file()

        self.__init_filename()

    @property
    def saving_time_step(self) -> float:
        return self.__saving_time_step

    @saving_time_step.setter
    def saving_time_step(self, saving_time_step: float) -> None:
        self.__saving_time_step = saving_time_step

    @property
    def overwrite_file(self) -> bool:
        return self.__overwrite_file

    @overwrite_file.setter
    def overwrite_file(self, overwrite_file: bool) -> None:
        self.__overwrite_file = overwrite_file

    @property
    def filename(self) -> str:
        return self.__filename

    @filename.setter
    def filename(self, filename: str) -> None:
        self.__filename = filename

    def __init_saving_time_step(self):
        if not self._config_parser.has_option("general", "saving_time_step") \
                or len(self._config_parser["general"]["saving_time_step"]) \
                == 0:
            self.__saving_time_step = self.SAVING_STEP_DEFAULT
        else:
            self.__saving_time_step = float(self._config_parser[
                                                "general"]["saving_time_step"])

    def __init_overwrite_file(self):
        if not self._config_parser.has_option("file", "overwrite") \
                or len(self._config_parser["file"]["overwrite"]) == 0:
            self.__overwrite_file = self.OVERWRITE_FILE_DEFAULT
        else:
            self.__overwrite_file = self._config_parser.getboolean(
                "file", "overwrite")

    def __init_filename(self):
        if not self._config_parser.has_option("file", "filename") \
                or len(self._config_parser["file"]["filename"]) == 0:
            self.__filename = self.FILENAME_DEFAULT
        else:
            self.__filename = self._config_parser.get("file", "filename")
