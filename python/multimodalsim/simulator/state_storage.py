import pickle
import random
import time

import jsonpickle
import logging
from typing import Optional, Any

import multimodalsim.simulator.environment as environment_module
import multimodalsim.simulator.event_queue as event_queue_module
from multimodalsim.config.state_storage_config import StateStorageConfig

import multimodalsim.observer.data_collector as data_collector_module
from multimodalsim.simulator.event import Event

logger = logging.getLogger(__name__)


class StateStorage:

    def __init__(self, save: bool, load: bool,
                 config: Optional[str | StateStorageConfig]):
        self.__queue = None
        self.__env = None
        self.__data_collector_data_containers = None
        self.__data_analyzer_data_containers = None

        self.__save = save
        self.__load = load

        self._load_config(config)

        self.__previous_saving_time = None

    def load_state(self, state_file_name: str):
        logger.info("load_state: {}".format(state_file_name))
        self.__load = True
        self._load_state(state_file_name)

    def _load_state(self, state_file_name: str):
        raise NotImplementedError('_save_state of {} not implemented'.
                                  format(self.__class__.__name__))

    def save_state(self):
        if self.need_to_save:
            logger.info("save_state: {}".format(self.__env.current_time))
            self._save_state()
            self.__previous_saving_time = self.__env.current_time

    def _save_state(self):
        raise NotImplementedError('_save_state of {} not implemented'.
                                  format(self.__class__.__name__))

    @property
    def env(self) -> Optional['environment_module.Environment']:
        return self.__env

    @env.setter
    def env(self, env: Optional['environment_module.Environment']) -> None:
        self.__env = env

    @property
    def queue(self) -> Optional['event_queue_module.EventQueue']:
        return self.__queue

    @queue.setter
    def queue(self, queue: Optional['event_queue_module.EventQueue']) \
            -> None:
        self.__queue = queue

    @property
    def data_collector_data_containers(self) \
            -> Optional[list['data_collector_module.DataContainer']]:
        return self.__data_collector_data_containers

    @data_collector_data_containers.setter
    def data_collector_data_containers(
            self,
            data_collector_data_containers:
            Optional[list['data_collector_module.DataContainer']]) \
            -> None:
        self.__data_collector_data_containers = data_collector_data_containers

    @property
    def data_analyzer_data_containers(self) \
            -> Optional[list['data_collector_module.DataContainer']]:
        return self.__data_analyzer_data_containers

    @data_analyzer_data_containers.setter
    def data_analyzer_data_containers(
            self,
            data_analyzer_data_containers:
            Optional[list['data_collector_module.DataContainer']]) \
            -> None:
        self.__data_analyzer_data_containers = data_analyzer_data_containers

    @property
    def save(self) -> bool:
        return self.__save

    @save.setter
    def save(self, save: bool) -> None:
        self.__save = save

    @property
    def load(self) -> bool:
        return self.__load

    @load.setter
    def load(self, load: bool) -> None:
        self.__load = load

    @property
    def previous_saving_time(self) -> Optional[float]:
        return self.__previous_saving_time

    @property
    def need_to_save(self) -> bool:
        save = False
        if self.__previous_saving_time is None:
            save = True
        elif self.__env is not None \
                and (self.__env.current_time - self.__previous_saving_time
                     >= self.config.saving_time_step):
            save = True

        return save

    @property
    def config(self) -> Optional[StateStorageConfig]:
        return self.__config

    def _load_config(self, config):
        if isinstance(config, str):
            self.__config = StateStorageConfig(config)
        elif not isinstance(config, StateStorageConfig):
            self.__config = StateStorageConfig()


class StateStoragePickle(StateStorage):
    def __init__(self, saved_states_folder: str, save: bool = True,
                 load: bool = False,
                 config: Optional[str | StateStorageConfig] = None) -> None:
        super().__init__(save, load, config)

        self.saved_states_folder__ = saved_states_folder

    def _load_state(self, state_file_name: str):

        simulation_state = self.__load_from_file(state_file_name)

        self.env = simulation_state.env

        events = simulation_state.queue_data.events
        index = simulation_state.queue_data.index
        self.queue = event_queue_module.EventQueue(self.env, events, index)

        self.data_collector_data_containers = \
            simulation_state.data_collector_data_containers
        self.data_analyzer_data_containers = \
            simulation_state.data_analyzer_data_containers
        random.setstate(simulation_state.random_state)

    def _save_state(self):
        env_copy = self.env.get_environment_copy()
        queue_copy = self.queue.get_queue_copy()

        queue_data = QueueData(queue_copy.events, queue_copy.index)

        random_state = random.getstate()

        # Make the DataContainer objects pickable (for example, remove the
        # DataFrame objects) before saving to file.
        for data_container in self.data_collector_data_containers:
            data_container.make_pickable()

        for data_container in self.data_analyzer_data_containers:
            data_container.make_pickable()

        simulation_state = SimulationState(env_copy, queue_data,
                                           self.data_collector_data_containers,
                                           self.data_analyzer_data_containers,
                                           random_state)

        self.__save_to_file(simulation_state)

    def __load_from_file(self, state_file_name):
        state_file_path = self.saved_states_folder__ + state_file_name

        if self.config.json:
            simulation_state = self.__load_from_json_file(state_file_path)
        else:
            simulation_state = self.__load_from_pkl_file(state_file_path)

        return simulation_state

    def __load_from_json_file(self, state_file_path):
        with open(state_file_path, 'r') as json_file:
            json_string = json_file.read()
            simulation_state = jsonpickle.decode(json_string)

        return simulation_state

    def __load_from_pkl_file(self, state_file_path):
        with open(state_file_path, 'rb') as pkl_file:
            simulation_state = pickle.load(pkl_file)

        return simulation_state

    def __save_to_file(self, simulation_state):
        filename = self.config.filename
        if not self.config.overwrite_file:
            filename += "_" + str(self.env.current_time)

        if self.config.json:
            self.__save_to_json_file(simulation_state, filename)
        else:
            self.__save_to_pkl_file(simulation_state, filename)

    def __save_to_json_file(self, simulation_state, filename):
        with open(self.saved_states_folder__ + filename + ".json", 'w') \
                as json_file:
            t1 = time.time()
            json_string = jsonpickle.encode(simulation_state,
                                            indent=self.config.indent)
            t2 = time.time()
            json_file.write(json_string)
            t3 = time.time()

    def __save_to_pkl_file(self, simulation_state, filename):
        with open(self.saved_states_folder__ + filename + ".pkl", 'wb') \
                as pklfile:
            t1 = time.time()
            pickle.dump(simulation_state, pklfile)
            t2 = time.time()


class QueueData:
    def __init__(self, events: list['Event'], index: int):
        self.__events = events
        self.__index = index

    @property
    def events(self):
        return self.__events

    @property
    def index(self):
        return self.__index


class SimulationState:
    def __init__(self, env: 'environment_module.Environment',
                 queue_data: QueueData,
                 data_collector_data_containers:
                 list['data_collector_module.DataContainer'],
                 data_analyzer_data_containers:
                 list['data_collector_module.DataContainer'],
                 random_state: Optional[tuple[Any, ...]]):
        self.__env = env
        self.__queue_data = queue_data
        self.__data_collector_data_containers = data_collector_data_containers
        self.__data_analyzer_data_containers = data_analyzer_data_containers
        self.__random_state = random_state

    @property
    def env(self) -> 'environment_module.Environment':
        return self.__env

    @property
    def queue_data(self) -> QueueData:
        return self.__queue_data

    @property
    def data_collector_data_containers(self) \
            -> list['data_collector_module.DataContainer']:
        return self.__data_collector_data_containers

    @property
    def data_analyzer_data_containers(self) \
            -> list['data_collector_module.DataContainer']:
        return self.__data_analyzer_data_containers

    @property
    def random_state(self) -> Optional[tuple[Any, ...]]:
        return self.__random_state
