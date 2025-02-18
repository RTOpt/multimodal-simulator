import logging
import threading
from typing import Optional, Any

from multimodalsim.config.simulation_config import SimulationConfig
from multimodalsim.observer.data_collector import DataCollector, DataContainer
from multimodalsim.observer.environment_observer import EnvironmentObserver
from multimodalsim.observer.visualizer import Visualizer
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.coordinates.coordinates import Coordinates
from multimodalsim.simulator.environment import Environment
from multimodalsim.simulator.event import RecurrentTimeSyncEvent
from multimodalsim.simulator.event_queue import EventQueue
from multimodalsim.simulator.optimization_event import Optimize

from multimodalsim.simulator.passenger_event import PassengerRelease
from multimodalsim.simulator.request import Trip
from multimodalsim.simulator.state_storage import StateStorage
from multimodalsim.simulator.travel_times import TravelTimes
from multimodalsim.simulator.vehicle import Vehicle, Route
from multimodalsim.simulator.vehicle_event import VehicleReady

logger = logging.getLogger(__name__)


class Simulation:

    def __init__(self, optimization: Optimization, trips: list[Trip],
                 vehicles: list[Vehicle],
                 routes_by_vehicle_id: dict[str | int, Route],
                 network: Optional[Any] = None,
                 environment_observer:
                 Optional['env_obs_module.EnvironmentObserver'] = None,
                 coordinates: Optional[Coordinates] = None,
                 travel_times: Optional[TravelTimes] = None,
                 state_storage: Optional[StateStorage] = None,
                 config: Optional[str | SimulationConfig] = None) -> None:

        self.__state_storage = state_storage

        self.__env = Environment(optimization, network=network,
                                 coordinates=coordinates,
                                 travel_times=travel_times,
                                 state_storage=state_storage)

        self.__init_queue()

        self.__init_environment_observer(environment_observer)

        self.__init_state_storage_from_env()

        self.__load_config(config)

        if state_storage is None or not state_storage.load:
            self.__create_vehicle_ready_events(vehicles, routes_by_vehicle_id)
            self.__create_passenger_release_events(trips)
            self.__initialize_time(vehicles, trips)

        # To control the execution of the simulation (pause, resume, stop)
        self.__simulation_cv = threading.Condition()
        self.__simulation_paused = False
        self.__simulation_stopped = False

    @property
    def data_collectors(self) -> Optional[list[DataCollector]]:
        if self.__environment_observer is not None:
            data_collectors = self.__environment_observer.data_collectors
        else:
            data_collectors = None
        return data_collectors

    def simulate(self, max_time: Optional[float] = None) -> None:
        self.__config.max_time = self.__max_time if max_time is None \
            else max_time

        # main loop of the simulation
        while not self.__queue.is_empty():

            try:

                self.__check_if_paused()

                with self.__simulation_cv:
                    if self.__simulation_stopped:
                        break

                self.__save_state_if_needed()

                current_event = self.__queue.pop()

                self.__env.current_time = current_event.time

                if self.__config.max_time is not None \
                        and self.__env.current_time > self.__config.max_time:
                    break

                self.__visualize_environment(current_event,
                                             current_event.index,
                                             current_event.priority)

                process_event = current_event.process(self.__env)
                logger.debug("process_event: {}".format(process_event))
                self.__collect_data(current_event, current_event.index,
                                    current_event.priority)
            except Exception as exception:
                self.__save_state_on_exception(exception)
                raise

        logger.info("\n***************\nEND OF SIMULATION\n***************")
        self.__visualize_environment()

    def pause(self):
        logger.info("Simulation paused")
        with self.__simulation_cv:
            self.__simulation_paused = True

    def resume(self):
        logger.info("Simulation resumed")
        with self.__simulation_cv:
            self.__simulation_paused = False
            self.__simulation_cv.notify()

    def stop(self):
        logger.info("Simulation stopped")
        with self.__simulation_cv:
            # If simulation is paused, resume it first so that it can be
            # stopped.
            self.__simulation_paused = False
            self.__simulation_cv.notify()

            self.__simulation_stopped = True

    def __init_queue(self):
        if self.__state_storage is not None and self.__state_storage.load:
            events = self.__state_storage.queue.events
            index = self.__state_storage.queue.index
        else:
            events = None
            index = None

        self.__queue = EventQueue(self.__env, events, index)

    def __load_config(self, config):
        if isinstance(config, str):
            self.__config = SimulationConfig(config)
        elif not isinstance(config, SimulationConfig):
            self.__config = SimulationConfig()
        else:
            self.__config = config

        self.__max_time = self.__config.max_time
        self.__speed = self.__config.speed
        self.__time_step = self.__config.time_step
        self.__update_position_time_step = \
            self.__config.update_position_time_step

    def __create_vehicle_ready_events(self, vehicles, routes_by_vehicle_id):
        for vehicle in vehicles:
            route = routes_by_vehicle_id[vehicle.id] \
                if vehicle.id in routes_by_vehicle_id else None

            VehicleReady(vehicle, route, self.__queue,
                         self.__update_position_time_step).add_to_queue()

    def __create_passenger_release_events(self, trips):
        for trip in trips:
            PassengerRelease(trip, self.__queue).add_to_queue()

    def __initialize_time(self, vehicles, trips):
        first_vehicle_event_time = self.__find_smallest_release_time(vehicles)
        first_event_time = self.__find_smallest_release_time(
            trips, first_vehicle_event_time)

        self.__env.current_time = first_event_time

        if self.__time_step is not None:
            RecurrentTimeSyncEvent(self.__queue, first_event_time,
                                   self.__time_step,
                                   self.__speed).add_to_queue()

    def __find_smallest_release_time(self, objects_list,
                                     smallest_release_time=None):
        if smallest_release_time is None:
            smallest_release_time = objects_list[0].release_time \
                if len(objects_list) > 0 else None

        for obj in objects_list:
            if obj.release_time < smallest_release_time:
                smallest_release_time = obj.release_time

        return smallest_release_time

    def __visualize_environment(self, current_event=None, event_index=None,
                                event_priority=None):
        if self.__environment_observer is not None \
                and self.__environment_observer.visualizers is not None:
            for visualizer in self.__environment_observer.visualizers:
                visualizer.visualize_environment(self.__env, current_event,
                                                 event_index,
                                                 event_priority)

    def __collect_data(self, current_event=None, event_index=None,
                       event_priority=None):
        if self.__environment_observer is not None \
                and self.__environment_observer.data_collectors is not None:
            for data_collector in self.__environment_observer.data_collectors:
                data_collector.collect(self.__env, current_event,
                                       event_index, event_priority)

    def __check_if_paused(self):
        with self.__simulation_cv:
            if self.__simulation_paused:
                self.__simulation_cv.wait()

    def __init_environment_observer(self, environment_observer):

        if environment_observer is not None:
            for visualizer in environment_observer.visualizers:
                visualizer.attach_simulation(self)
                visualizer.attach_environment(self.__env)

        self.__environment_observer = environment_observer

        if self.__state_storage is not None and self.__state_storage.load:
            self.__init_data_collectors_from_state_storage()
            self.__init_visualizers_from_state_storage()

    def __init_data_collectors_from_state_storage(self):
        if isinstance(self.__state_storage.data_collector_data_containers,
                      DataContainer):
            dc_data_containers = \
                [self.__state_storage.data_collector_data_containers]
        else:
            dc_data_containers = \
                self.__state_storage.data_collector_data_containers

        if isinstance(self.__environment_observer.data_collectors,
                      DataCollector):
            data_collectors = [self.__environment_observer.data_collectors]
        else:
            data_collectors = self.__environment_observer.data_collectors

        for data_collector, data_container in zip(data_collectors,
                                                  dc_data_containers):
            data_collector.data_container = data_container

    def __init_visualizers_from_state_storage(self):
        if isinstance(self.__state_storage.data_collector_data_containers,
                      DataContainer):
            da_data_containers = \
                [self.__state_storage.data_collector_data_containers]
        else:
            da_data_containers = \
                self.__state_storage.data_collector_data_containers

        if isinstance(self.__environment_observer.visualizers,
                      Visualizer):
            visualizers = [self.__environment_observer.visualizers]
        else:
            visualizers = self.__environment_observer.visualizers

        for visualizer, data_container in zip(visualizers, da_data_containers):
            visualizer.data_analyzer.data_container = data_container

    def __init_state_storage_from_env(self):

        if self.__state_storage is not None:

            if self.__env.optimization.config.asynchronous:
                raise ValueError("A state storage cannot be used with "
                                 "asynchronous optimization!")

            self.__state_storage.env = self.__env
            self.__state_storage.queue = self.__queue
            self.__init_state_storage_data_collector_data_containers()
            self.__init_state_storage_data_analyzer_data_containers()

    def __init_state_storage_data_collector_data_containers(self):
        self.__state_storage.data_collector_data_containers = []
        for data_collector in self.__environment_observer.data_collectors:
            self.__state_storage.data_collector_data_containers.append(
                data_collector.data_container)

    def __init_state_storage_data_analyzer_data_containers(self):
        self.__state_storage.data_analyzer_data_containers = []
        for visualizer in self.__environment_observer.visualizers:
            self.__state_storage.data_analyzer_data_containers.append(
                visualizer.data_analyzer.data_container)

    def __save_state_if_needed(self):
        next_event = self.__queue[0]
        if self.__env.state_storage is not None \
                and self.__env.state_storage.config.saving_periodically \
                and self.__env.state_storage.save \
                and isinstance(next_event, Optimize):
            self.__env.state_storage.save_state()

    def __save_state_on_exception(self, exception):
        if self.__state_storage is not None \
                and self.__state_storage.config.saving_on_exception \
                and self.__state_storage.save:
            self.__state_storage.save_state(exception=exception)
