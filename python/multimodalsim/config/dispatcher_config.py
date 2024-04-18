from multimodalsim.config.config import Config

import os

class DispatcherConfig(Config):
    def __init__(self, config_file=os.path.join(os.path.dirname(__file__),
                                                "ini/dispatcher.ini")):
        super().__init__(config_file)

    @property
    def speedup_factor(self):
        return int(self._config_parser["speedup"]["speedup_factor"])