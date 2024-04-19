from multimodalsim.config.config import Config

import os

class FixedLineDispatcherConfig(Config):
    def __init__(self, config_file=os.path.join(os.path.dirname(__file__),
                                                "ini/fixed_line_dispatcher.ini")):
        super().__init__(config_file)

    @property
    def speedup_factor(self):
        # Return the speedup factor (float)
        return float(self._config_parser["speedup"]["speedup_factor"])
    
    @property
    def walking_speed(self):
        # Return the speedup factor (float)
        return float(self._config_parser["skip-stop"]["walking_speed"])