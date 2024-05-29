from multimodalsim.config.config import Config

import os

class FixedLineDispatcherConfig(Config):
    def __init__(self, config_file=os.path.join(os.path.dirname(__file__),
                                                "ini/fixed_line_dispatcher.ini")):
        super().__init__(config_file)

    def get_horizon(self, ss, sp):
        if ss or sp:
            return int(self._config_parser["speedup"]["horizon"])
        else:
            return int(self._config_parser["general"]["horizon"])
        
    def get_speedup_factor(self, sp):
        # Return the speedup factor (float)
        if sp:
            return float(self._config_parser["speedup"]["speedup_factor"])
        else:
            return float(self._config_parser["general"]["speedup_factor"])
    
    def get_skip_stop(self, ss):
        # Return the skip stop (bool)
        if ss:
            return bool(self._config_parser["skip-stop"]["skip_stop"])
        else:
            return bool(self._config_parser["general"]["skip_stop"])
    
    def get_general_parameters(self):
        parameters = {
            "k": int(self._config_parser["general"]["k"]), # nombre de clusters par jour
            "dimension": int(self._config_parser["general"]["dimension"]), # dimension des clusters 
            "nbr_bus": int(self._config_parser["general"]["nbr_bus"]), # nombre de bus par simulation
            "pas": int(self._config_parser["general"]["pas"]),
            "prix_hors_bus": int(self._config_parser["general"]["prix_hors_bus"]),
            "price": int(self._config_parser["general"]["price"]),
            "walking_speed": float(self._config_parser["general"]["walking_speed"])
        }

        return parameters
    
    def get_algo_parameters(self, algo):
        if algo == 2:
            name ='regret'
        elif algo == 1:
            name = 'deterministic'
        elif algo == 0:
            name = 'offline'
        algo_parameters = {
            "type_intervalles": int(self._config_parser[name]["type_intervalles"]), #always known beforehand
            "type_dwell": int(self._config_parser[name]["type_dwell"]),
            "type_tps_parcours": int(self._config_parser[name]["type_tps_parcours"]),
            "type_m": int(self._config_parser[name]["type_m"]),
            "type_d": int(self._config_parser[name]["type_d"]),
            "type_tm": int(self._config_parser[name]["type_tm"]),
            "type_td": int(self._config_parser[name]["type_td"]),
            "type_ttime": int(self._config_parser[name]["type_ttime"]),
            "folder_name_addendum": self._config_parser[name]["folder_name_addendum"],
            "j_try": int(self._config_parser[name]["j_try"]),
            "nbr_simulations": int(self._config_parser[name]["nbr_simulations"])
        }
        return algo_parameters