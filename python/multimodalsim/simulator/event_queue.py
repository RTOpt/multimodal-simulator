from queue import PriorityQueue

import multimodalsim.simulator.optimization_event_process as optimization_event_process


class EventQueue(object):
    def __init__(self, env):
        self.__queue = PriorityQueue()

        self.__index = 0

        self.__env = env

    @property
    def env(self):
        return self.__env

    def is_empty(self):
        """check if the queue is empty"""
        return self.__queue.empty()

    def put(self, event):
        """add an element in the queue"""
        # self.__queue.put((-event.time, event))

        time_priority = event.time
        event_type_priority = self.__get_event_type_priority(event)

        priority = time_priority + event_type_priority

        self.__queue.put((priority, self.__index, event))
        self.__index += 1

    def pop(self):
        """pop an element based on Priority time"""
        return self.__queue.get()

    def is_event_type_in_queue(self, event_type, time):
        is_in_queue = False
        for _, _, event in self.__queue.queue:
            if event.time == time and isinstance(event, event_type):
                is_in_queue = True
                break

        return is_in_queue

    def __get_event_type_priority(self, event):

        event_type_priority = 0
        if isinstance(event, optimization_event_process.Optimize):
            event_type_priority = 0.5

        return event_type_priority

