import logging
from typing import Optional, Any

from multimodalsim.config.simulation_config import SimulationConfig
from multimodalsim.observer.data_collector import DataCollector
from multimodalsim.observer.environment_observer import EnvironmentObserver
from multimodalsim.optimization.optimization import Optimization
from multimodalsim.simulator.coordinates import Coordinates
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
                 environment_observer: Optional[EnvironmentObserver] = None,
                 coordinates: Optional[Coordinates] = None,
                 travel_times: Optional[TravelTimes] = None,
                 state_storage: Optional[StateStorage] = None,
                 save_simulation: bool = False,
                 config: Optional[str | SimulationConfig] = None) -> None:

        if state_storage is not None:
            env_copy = state_storage.env
            queue_copy = state_storage.queue
        else:
            env_copy = None
            queue_copy = None

        if save_simulation:
            self.__env = Environment(optimization, network=network,
                                     coordinates=coordinates,
                                     travel_times=travel_times,
                                     state_storage=state_storage,
                                     env_copy=env_copy)
        else:
            self.__env = Environment(optimization, network=network,
                                     coordinates=coordinates,
                                     travel_times=travel_times,
                                     env_copy=env_copy)

        self.__queue = EventQueue(self.__env, queue_copy)

        self.__environment_observer = environment_observer

        self.__load_config(config)

        if state_storage is None or state_storage.env is None:
            self.__create_vehicle_ready_events(vehicles, routes_by_vehicle_id)
            self.__create_passenger_release_events(trips)
            self.__initialize_time(vehicles, trips)

        self.__init_state_storage(state_storage, save_simulation)

    @property
    def data_collectors(self) -> Optional[list[DataCollector]]:
        if self.__environment_observer is not None:
            data_collectors = self.__environment_observer.data_collectors
        else:
            data_collectors = None
        return data_collectors

    def simulate(self, max_time: Optional[float] = None) -> None:
        max_time = self.__max_time if max_time is None else max_time

        # main loop of the simulation
        while not self.__queue.is_empty():

            next_event = self.__queue[0]
            self.__save_state_if_needed(next_event)

            current_event = self.__queue.pop()

            self.__env.current_time = current_event.time

            if max_time is not None and self.__env.current_time > max_time:
                break

            self.__visualize_environment(current_event, current_event.index,
                                         current_event.priority)

            process_event = current_event.process(self.__env)
            logger.debug("process_event: {}".format(process_event))
            self.__collect_data(current_event, current_event.index,
                                current_event.priority)

        logger.info("\n***************\nEND OF SIMULATION\n***************")
        self.__visualize_environment()

    def __load_config(self, config):
        if isinstance(config, str):
            config = SimulationConfig(config)
        elif not isinstance(config, SimulationConfig):
            config = SimulationConfig()

        self.__max_time = config.max_time
        self.__speed = config.speed
        self.__time_step = config.time_step
        self.__update_position_time_step = config.update_position_time_step

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
        if self.__environment_observer is not None:
            for visualizer in self.__environment_observer.visualizers:
                visualizer.visualize_environment(self.__env, current_event,
                                                 event_index,
                                                 event_priority)

    def __collect_data(self, current_event=None, event_index=None,
                       event_priority=None):
        if self.__environment_observer is not None:
            for data_collector in self.__environment_observer.data_collectors:
                data_collector.collect(self.__env, current_event,
                                       event_index, event_priority)

    def __init_state_storage(self, state_storage, save_simulation):

        if save_simulation and state_storage is not None:
            self.__state_storage = state_storage
            self.__state_storage.env = self.__env
            self.__state_storage.queue = self.__queue

    def __save_state_if_needed(self, current_event):
        if self.__env.state_storage is not None \
                and isinstance(current_event, Optimize):
            self.__env.state_storage.save_state()
