import logging

from multimodalsim.simulator.environment import Environment
from multimodalsim.simulator.event_queue import EventQueue

from multimodalsim.simulator.passenger_event import PassengerRelease
from multimodalsim.simulator.vehicle_event import VehicleReady
from multimodalsim.observer.data_collector import StandardDataCollector

logger = logging.getLogger(__name__)


class Simulation(object):

    def __init__(self, opt, trips, vehicles, network=None,
                 environment_observer=None, available_connections=None):

        self.__env = Environment(opt, network)
        self.__queue = EventQueue(self.__env)
        self.__environment_observer = environment_observer
        self.__available_connections = available_connections

        for vehicle in vehicles:
            VehicleReady(vehicle, self.__queue).add_to_queue()

        for trip in trips:
            PassengerRelease(trip, self.__queue).add_to_queue()

    @property
    def data_collectors(self):
        return self.__environment_observer.data_collectors

    def simulate(self):
        # main loop of the simulation
        while not self.__queue.is_empty():
            current_event = self.__queue.pop()

            self.__visualize_environment(current_event, current_event.index,
                                         current_event.priority)

            self.__env.current_time = current_event.time

            process_event = current_event.process(self.__env)
            logger.debug("process_event: {}".format(process_event))
            self.__collect_data(current_event, current_event.index,
                                current_event.priority)

        logger.info("\n***************\nEND OF SIMULATION\n***************")
        self.__visualize_environment()

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
