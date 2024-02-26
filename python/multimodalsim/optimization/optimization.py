import logging

from multimodalsim.config.optimization_config import OptimizationConfig
from multimodalsim.optimization.splitter import OneLegSplitter
from multimodalsim.state_machine.state_machine import OptimizationStateMachine

logger = logging.getLogger(__name__)


class Optimization(object):

    def __init__(self, dispatcher, splitter=None, freeze_interval=None,
                 config=None):
        self.__dispatcher = dispatcher
        self.__splitter = OneLegSplitter() if splitter is None else splitter

        self.__state_machine = OptimizationStateMachine(self)

        self.__state = None

        self.__config = OptimizationConfig() if config is None else config
        self.__freeze_interval = freeze_interval \
            if freeze_interval is not None else self.__config.freeze_interval

    @property
    def status(self):
        return self.__state_machine.current_state.status

    @property
    def state_machine(self):
        return self.__state_machine

    @property
    def freeze_interval(self):
        return self.__freeze_interval

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, state):
        self.__state = state

    def split(self, request, state):
        return self.__splitter.split(request, state)

    def dispatch(self, state):
        return self.__dispatcher.dispatch(state)

    def need_to_optimize(self, env_stats):
        # By default, reoptimize every time the Optimize event is processed.
        return True

    @property
    def splitter(self):
        return self.__splitter

    @property
    def dispatcher(self):
        return self.__dispatcher

    @property
    def config(self):
        return self.__config


class OptimizationResult(object):

    def __init__(self, state, modified_requests, modified_vehicles):
        self.state = state
        self.modified_requests = modified_requests
        self.modified_vehicles = modified_vehicles
