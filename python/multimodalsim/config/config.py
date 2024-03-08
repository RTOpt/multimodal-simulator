import configparser


class Config:

    def __init__(self, config_file: str):
        self.__config_file = config_file
        self._config_parser = configparser.ConfigParser()
        self._config_parser.read(self.__config_file)
