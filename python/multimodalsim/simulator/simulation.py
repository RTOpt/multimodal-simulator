import logging

from multimodalsim.config.simulation_config import SimulationConfig
from multimodalsim.simulator.environment import Environment
from multimodalsim.simulator.event import RecurrentTimeSyncEvent
from multimodalsim.simulator.event_queue import EventQueue
from multimodalsim.simulator.optimization_event import Optimize

from multimodalsim.simulator.passenger_event import PassengerRelease
from multimodalsim.simulator.vehicle_event import VehicleReady

logger = logging.getLogger(__name__)


class Simulation(object):

    def __init__(self, optimization, trips, vehicles, routes_by_vehicle_id,
                 network=None, environment_observer=None, coordinates=None,
                 travel_times=None, config=None, main_line=None, next_main_line=None):

        self.__env = Environment(optimization, network=network,
                                 coordinates=coordinates,
                                 travel_times=travel_times,
                                 main_line=main_line,
                                 next_main_line=next_main_line)
        self.__queue = EventQueue(self.__env)
        self.__environment_observer = environment_observer

        config = SimulationConfig() if config is None else config
        self.__load_config(config)

        for vehicle in vehicles:
            route = routes_by_vehicle_id[vehicle.id] \
                if vehicle.id in routes_by_vehicle_id else None

            VehicleReady(vehicle, route, self.__queue,
                         self.__update_position_time_step).add_to_queue()
        for trip in trips:
            PassengerRelease(trip, self.__queue).add_to_queue()
        first_vehicle_event_time = self.__find_smallest_release_time(vehicles)
        first_event_time = self.__find_smallest_release_time(
            trips, first_vehicle_event_time)

        self.__env.current_time = first_event_time

        RecurrentTimeSyncEvent(self.__queue, first_event_time,
                               self.__speed,
                               self.__time_step).add_to_queue()

    @property
    def data_collectors(self):
        return self.__environment_observer.data_collectors

    def simulate(self, max_time=None, asynchronous=False):
        max_time = self.__max_time if max_time is None else max_time

        # main loop of the simulation
        while not self.__queue.is_empty():

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
        self.__max_time = config.max_time
        self.__speed = config.speed
        self.__time_step = config.time_step
        self.__update_position_time_step = config.update_position_time_step

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
        for visualizer in self.__environment_observer.visualizers:
            visualizer.visualize_environment(self.__env, current_event,
                                             event_index,
                                             event_priority)

    def __collect_data(self, current_event=None, event_index=None,
                       event_priority=None):
        for data_collector in self.__environment_observer.data_collectors:
            data_collector.collect(self.__env, current_event,
                                   event_index, event_priority)
