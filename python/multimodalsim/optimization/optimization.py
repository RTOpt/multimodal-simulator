import logging
from typing import Optional, Union

from multimodalsim.config.optimization_config import OptimizationConfig
import multimodalsim.optimization.dispatcher as dispatcher_module
from multimodalsim.optimization.splitter import Splitter, OneLegSplitter
import multimodalsim.state_machine.state_machine as state_machine
import multimodalsim.optimization.state as state_module
import multimodalsim.simulator.request as request
import multimodalsim.simulator.environment as environment_module
import multimodalsim.simulator.vehicle as vehicle_module
from multimodalsim.state_machine.status import OptimizationStatus

logger = logging.getLogger(__name__)


class Optimization:

    def __init__(self, dispatcher: 'dispatcher_module.Dispatcher',
                 splitter: Optional[Splitter] = None,
                 freeze_interval: Optional[float] = None,
                 config: Optional[str | OptimizationConfig] = None) -> None:
        self.__dispatcher = dispatcher
        self.__splitter = OneLegSplitter() if splitter is None else splitter

        self.__state_machine = state_machine.OptimizationStateMachine(self)

        self.__state = None

        self.__load_config(config, freeze_interval)

    @property
    def status(self) -> OptimizationStatus:
        return self.__state_machine.current_state.status

    @property
    def state_machine(self) -> 'state_machine.StateMachine':
        return self.__state_machine

    @property
    def freeze_interval(self) -> float:
        return self.__freeze_interval

    @property
    def state(self) -> 'state_module.State':
        return self.__state

    @state.setter
    def state(self, state: 'state_module.State') -> None:
        self.__state = state

    def split(
            self, trip: 'request.Trip',
            state: Union[
                'state_module.State', 'environment_module.Environment']) \
            -> list['request.Leg']:
        return self.__splitter.split(trip, state)

    def dispatch(self, state: 'state_module.State') -> 'OptimizationResult':
        return self.__dispatcher.dispatch(state)

    def need_to_optimize(
            self, env_stats: 'environment_module.EnvironmentStatistics') \
            -> bool:
        # By default, reoptimize every time the Optimize event is processed.
        return True

    @property
    def splitter(self) -> Splitter:
        return self.__splitter

    @property
    def dispatcher(self) -> 'dispatcher_module.Dispatcher':
        return self.__dispatcher

    @property
    def config(self) -> OptimizationConfig:
        return self.__config

    def __load_config(self, config, freeze_interval):
        if isinstance(config, str):
            self.__config = OptimizationConfig(config)
        elif not isinstance(config, OptimizationConfig):
            self.__config = OptimizationConfig()
        else:
            self.__config = config

        self.__freeze_interval = freeze_interval \
            if freeze_interval is not None else self.__config.freeze_interval


class OptimizationResult:

    def __init__(self, state: 'state_module.State',
                 modified_requests: list['request.Trip'],
                 modified_vehicles: list['vehicle_module.Vehicle']):
        self.state = state
        self.modified_requests = modified_requests
        self.modified_vehicles = modified_vehicles
