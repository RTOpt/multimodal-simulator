from queue import PriorityQueue

from multimodalsim.simulator.event import ActionEvent


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
        event.index = self.__index
        self.__queue.put(event)
        self.__index += 1

    def pop(self):
        """pop an element based on Priority time"""
        return self.__queue.get()

    def is_event_type_in_queue(self, event_type, time=None, owner=None):
        is_in_queue = False
        for event in self.__queue.queue:
            if owner is not None \
                    and isinstance(event, ActionEvent) \
                    and event.state_machine.owner == owner \
                    and self.__is_event_looked_for(event, event_type, time):
                is_in_queue = True
                break
            elif owner is None \
                    and self.__is_event_looked_for(event, event_type, time):
                is_in_queue = True
                break

        return is_in_queue

    def cancel_event_type(self, event_type, time=None, owner=None):
        events_to_be_cancelled = []
        for event in self.__queue.queue:
            if owner is not None \
                    and isinstance(event, ActionEvent) \
                    and event.state_machine.owner == owner \
                    and self.__is_event_looked_for(event, event_type, time):
                events_to_be_cancelled.append(event)
            elif owner is None \
                    and self.__is_event_looked_for(event, event_type, time):
                events_to_be_cancelled.append(event)

        self.cancel_events(events_to_be_cancelled)

    def cancel_events(self, events):
        for event in events:
            event.cancelled = True

    def __is_event_looked_for(self, event, event_type, time):
        is_event = False
        if time is not None and event.time == time \
                and isinstance(event, event_type):
            is_event = True
        elif time is None and isinstance(event, event_type):
            is_event = True
        return is_event
