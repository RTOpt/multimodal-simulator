import logging

from multimodalsim.simulator.environment import Environment
from multimodalsim.simulator.event_queue import EventQueue

from multimodalsim.simulator.passenger_event_process import PassengerRelease
from multimodalsim.simulator.vehicle_event_process import VehicleReady

logger = logging.getLogger(__name__)


class Simulation(object):

    def __init__(self, opt, trips, vehicles, network=None, visualizer=None):

        self.__env = Environment(opt, network)
        self.__queue = EventQueue(self.__env)
        self.__visualizer = visualizer

        for vehicle in vehicles:
            VehicleReady(vehicle, self.__queue).add_to_queue()

        for trip in trips:
            PassengerRelease(trip, self.__queue).add_to_queue()

    def simulate(self):
        # main loop of the simulation
        while not self.__queue.is_empty():
            event_time, event_index, current_event = self.__queue.pop()

            self.__visualize_environment(event_time, event_index, current_event)

            self.__env.current_time = event_time

            process_event = current_event.process(self.__env)
            logger.debug("process_event: {}".format(process_event))

        logger.info("\n***************\nEND OF SIMULATION\n***************")
        self.__visualize_environment()

    def __visualize_environment(self, event_time=None, event_index=None, current_event=None):
        if self.__visualizer is not None:
            self.__visualizer.visualize_environment(self.__env, event_time, event_index, current_event)