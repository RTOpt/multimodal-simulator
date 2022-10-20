import logging

from multimodalsim.simulator.environment import Environment
from multimodalsim.simulator.event_queue import EventQueue

from multimodalsim.simulator.passenger_event_process import PassengerRelease
from multimodalsim.simulator.vehicle_event_process import VehicleReady
from multimodalsim.statistics.data_collector import StandardDataCollector

logger = logging.getLogger(__name__)


class Simulation(object):

    def __init__(self, opt, trips, vehicles, network=None, visualizer=None,
                 data_collector=StandardDataCollector()):

        self.__env = Environment(opt, network)
        self.__queue = EventQueue(self.__env)
        self.__visualizer = visualizer
        self.__data_collector = data_collector

        for vehicle in vehicles:
            VehicleReady(vehicle, self.__queue).add_to_queue()

        for trip in trips:
            PassengerRelease(trip, self.__queue).add_to_queue()

    @property
    def data_collector(self):
        return self.__data_collector

    def simulate(self):
        # main loop of the simulation
        while not self.__queue.is_empty():
            event_priority, event_index, current_event = self.__queue.pop()
            event_time = current_event.time

            self.__visualize_environment(current_event, event_index,
                                         event_priority)

            self.__env.current_time = event_time

            process_event = current_event.process(self.__env)
            logger.debug("process_event: {}".format(process_event))
            self.__collect_data(current_event, event_index, event_priority)

        logger.info("\n***************\nEND OF SIMULATION\n***************")
        self.__visualize_environment()

    def __visualize_environment(self, current_event=None, event_index=None,
                                event_priority=None):
        if self.__visualizer is not None:
            self.__visualizer.visualize_environment(self.__env, current_event,
                                                    event_index,
                                                    event_priority)

    def __collect_data(self, current_event=None, event_index=None,
                       event_priority=None):
        if self.__data_collector is not None:
            self.__data_collector.collect(self.__env, current_event,
                                          event_index, event_priority)
