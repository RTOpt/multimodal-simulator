from multimodalsim.config.config import Config

import os


class StateStorageConfig(Config):

    SAVING_PERIODICALLY = True
    SAVING_ON_EXCEPTION = True
    SAVING_STEP_DEFAULT = 5
    OVERWRITE_FILE_DEFAULT = True
    FILENAME_DEFAULT = "state"
    INDENT_DEFAULT = 0
    JSON_DEFAULT = False

    def __init__(
            self,
            config_file: str = os.path.join(os.path.dirname(__file__),
                                            "ini/state_storage.ini")) -> None:
        super().__init__(config_file)

        self.__init_saving_periodically()

        self.__init_saving_on_exception()

        self.__init_saving_time_step()

        self.__init_overwrite_file()

        self.__init_filename()

        self.__init_indent()

        self.__init_json()

    @property
    def saving_periodically(self) -> bool:
        return self.__saving_periodically

    @saving_periodically.setter
    def saving_periodically(self, saving_periodically: bool) -> None:
        self.__saving_periodically = saving_periodically

    @property
    def saving_on_exception(self) -> bool:
        return self.__saving_on_exception

    @saving_on_exception.setter
    def saving_on_exception(self, saving_on_exception: bool) -> None:
        self.__saving_on_exception = saving_on_exception

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

    @property
    def indent(self) -> int:
        return self.__indent

    @indent.setter
    def indent(self, indent: int) -> None:
        self.__indent = indent

    @property
    def json(self) -> bool:
        return self.__json

    @json.setter
    def json(self, json: bool) -> None:
        self.__json = json

    def __init_saving_periodically(self):
        if not self._config_parser.has_option("general",
                                              "saving_periodically") \
                or len(self._config_parser["general"]["saving_periodically"]) \
                == 0:
            self.__saving_periodically = self.SAVING_PERIODICALLY
        else:
            self.__saving_periodically = self._config_parser.getboolean(
                "general", "saving_periodically")

    def __init_saving_on_exception(self):
        if not self._config_parser.has_option("general",
                                              "saving_on_exception") \
                or len(self._config_parser["general"]["saving_on_exception"]) \
                == 0:
            self.__saving_on_exception = self.SAVING_ON_EXCEPTION
        else:
            self.__saving_on_exception = self._config_parser.getboolean(
                "general", "saving_on_exception")

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

    def __init_indent(self):
        if not self._config_parser.has_option("file", "indent") \
                or len(self._config_parser["file"]["indent"]) == 0:
            self.__indent = self.INDENT_DEFAULT
        else:
            self.__indent = int(self._config_parser.get("file", "indent"))

    def __init_json(self):
        if not self._config_parser.has_option("file", "json") \
                or len(self._config_parser["file"]["json"]) == 0:
            self.__json = self.JSON_DEFAULT
        else:
            self.__json = self._config_parser.getboolean("file", "json")
