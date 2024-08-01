import logging
from multiprocessing import Pool
from typing import Optional, Union

from multimodalsim.config.optimization_config import OptimizationConfig
import multimodalsim.optimization.dispatcher as dispatcher_module
from multimodalsim.optimization.partition import Partition, PartitionSubset
from multimodalsim.optimization.splitter import Splitter, OneLegSplitter
import multimodalsim.state_machine.state_machine as state_machine
import multimodalsim.optimization.state as state_module
import multimodalsim.simulator.request as request
import multimodalsim.simulator.environment as environment_module
import multimodalsim.simulator.vehicle as vehicle_module
from multimodalsim.simulator.environment_statistics import \
    EnvironmentStatisticsExtractor, EnvironmentStatistics
from multimodalsim.state_machine.status import OptimizationStatus

logger = logging.getLogger(__name__)


class Optimization:
    """The ``Optimization`` class specifies the optimization algorithm that
    will be used during the simulation.
            Properties
            ----------
            dispatcher: Dispatcher
                Unique id
            splitter: Splitter
                Time at which the vehicle is ready to start
            freeze_interval: float
                Time interval during which the current state of the environment
                 is frozen.
            environment_statistics_extractor: EnvironmentStatisticsExtractor
                Object that extracts statistics from the environment. Used by
                the Optimize event to determine if an optimization is required.
            partition: Partition
                A partition of all the legs and all the vehicles. Used mainly
                in asyncrhonous simulations.
            config: OptimizationConfig or str
                Path to the config file or the OptimizationConfig object
                 itself.
        """

    def __init__(self, dispatcher: 'dispatcher_module.Dispatcher',
                 splitter: Optional[Splitter] = None,
                 freeze_interval: Optional[float] = None,
                 environment_statistics_extractor:
                 Optional[EnvironmentStatisticsExtractor] = None,
                 partition: Optional[Partition] = None,
                 config: Optional[str | OptimizationConfig] = None) -> None:
        self.__dispatcher = dispatcher
        self.__splitter = OneLegSplitter() if splitter is None else splitter

        if environment_statistics_extractor is None:
            # Use default EnvironmentStatisticsExtractor
            self.__environment_statistics_extractor = \
                EnvironmentStatisticsExtractor()
        else:
            self.__environment_statistics_extractor = \
                environment_statistics_extractor

        self.__partition = partition
        self.__create_state_machines()
        self.__create_state_variable()

        self.__load_config(config, freeze_interval)

        if self.__config.asynchronous:
            nb_processes = len(partition.subsets) if partition is not None \
                else 1
            self.__process_pool = Pool(processes=nb_processes)
        else:
            self.__process_pool = None

    @property
    def status(self) -> Union[OptimizationStatus, dict[OptimizationStatus]]:
        if isinstance(self.__state_machine, dict):
            ret = {}
            for name, subset_state_machine in self.__state_machine.items():
                ret[name] = subset_state_machine.current_state.status
        else:
            ret = self.__state_machine.current_state.status
        return ret

    @property
    def state_machine(self) -> Union['state_machine.StateMachine',
                                     dict['state_machine.StateMachine']]:
        return self.__state_machine

    @property
    def freeze_interval(self) -> float:
        return self.__freeze_interval

    @property
    def state(self) -> Union['state_module.State', dict['state_module.State']]:
        """Returns the State (of the environment) or, if a Partition is used,
        a dictionary with the State associated with each PartitionSubset."""
        return self.__state

    @state.setter
    def state(self, state: 'state_module.State') -> None:
        self.__state = state

    def get_state(self, partition_subset: Optional[PartitionSubset] = None):
        if partition_subset is not None:
            state = self.__state[partition_subset.id]
        else:
            state = self.__state

        return state

    def update_state(self, state: 'state_module.State',
                     partition_subset: Optional[PartitionSubset] = None):
        # Update the __state attribute with the state variable passed as
        # argument.
        if partition_subset is not None:
            self.__state[partition_subset.id] = state
        else:
            self.__state = state

    def split(
            self, trip: 'request.Trip',
            state: Union[
                'state_module.State', 'environment_module.Environment']) \
            -> list['request.Leg']:
        return self.__splitter.split(trip, state)

    def dispatch(self, state: 'state_module.State',
                 partition_subset: Optional[PartitionSubset] = None) \
            -> 'OptimizationResult':
        return self.__dispatcher.dispatch(state, partition_subset)

    def need_to_optimize(
            self, env_stats: EnvironmentStatistics) \
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
    def environment_statistics_extractor(self) \
            -> EnvironmentStatisticsExtractor:
        return self.__environment_statistics_extractor

    @property
    def partition(self) -> Partition:
        return self.__partition

    @property
    def process_pool(self) -> Pool:
        return self.__process_pool

    @property
    def config(self) -> OptimizationConfig:
        return self.__config

    def __create_state_machines(self):
        if self.__partition is None:
            self.__state_machine = \
                state_machine.OptimizationStateMachine(self)
        else:
            # If a Partition is used, one StateMachine by PartitionSubset is
            # created.
            self.__state_machine = {}
            for subset in self.__partition.subsets:
                self.__state_machine[subset.id] = \
                    state_machine.OptimizationStateMachine(subset)

    def __create_state_variable(self):
        if self.__partition is None:
            self.__state = None
        else:
            self.__state = {}

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

    def __init__(self, state: Optional['state_module.State'],
                 modified_requests: list['request.Trip'],
                 modified_vehicles: list['vehicle_module.Vehicle']):
        self.state = state
        self.modified_requests = modified_requests
        self.modified_vehicles = modified_vehicles
