import random

import jsonpickle
import logging
from typing import Optional, Any

import multimodalsim.simulator.environment as environment_module
import multimodalsim.simulator.event_queue as event_queue_module

logger = logging.getLogger(__name__)


class StateStorage:

    def __init__(self):
        self.__queue = None
        self.__env = None

    def save_state(self):
        raise NotImplementedError('save_state of {} not implemented'.
                                  format(self.__class__.__name__))

    def load_state(self, state_file_name: str):
        raise NotImplementedError('save_state of {} not implemented'.
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


class StateStorageJSON(StateStorage):
    def __init__(self, saved_states_folder: Optional[str] = None) -> None:
        super().__init__()

        self.saved_states_folder__ = saved_states_folder

        self.__nb_copies = 0

    def save_state(self):
        env_copy = self.env.get_environment_copy()
        queue_copy = self.queue.get_queue_copy()

        random_state = random.getstate()

        simulation_state = SimulationState(env_copy, queue_copy, random_state)

        with open(self.saved_states_folder__ + "state_{}.json".format(
                self.__nb_copies), 'w') as json_file:
            json_string = jsonpickle.encode(simulation_state, indent=4)
            json_file.write(json_string)

        self.__nb_copies += 1

    def load_state(self, state_file_name: str):

        with open(state_file_name, 'r') as json_file:
            json_string = json_file.read()
            simulation_state = jsonpickle.decode(json_string)

        self.env = simulation_state.env
        self.queue = simulation_state.queue
        random.setstate(simulation_state.random_state)


class SimulationState:
    def __init__(self, env: 'environment_module.Environment',
                 queue: 'event_queue_module.EventQueue',
                 random_state: Optional[tuple[Any, ...]]):
        self.__env = env
        self.__queue = queue
        self.__random_state = random_state

    @property
    def env(self) -> 'environment_module.Environment':
        return self.__env

    @property
    def queue(self) -> 'event_queue_module.EventQueue':
        return self.__queue

    @property
    def random_state(self) -> Optional[tuple[Any, ...]]:
        return self.__random_state
