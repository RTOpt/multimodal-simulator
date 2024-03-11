from queue import PriorityQueue
from typing import Type, Optional, Any

import multimodalsim.simulator.event as event_module
import multimodalsim.simulator.environment as environment


class EventQueue:
    def __init__(self, env: 'environment.Environment') -> None:
        self.__queue = PriorityQueue()

        self.__index = 0

        self.__env = env

    @property
    def env(self) -> 'environment.Environment':
        return self.__env

    def is_empty(self) -> bool:
        """check if the queue is empty"""
        return self.__queue.empty()

    def put(self, event: 'event_module.Event') -> None:
        """add an element in the queue"""
        event.index = self.__index
        self.__queue.put(event)
        self.__index += 1

    def pop(self) -> 'event_module.Event':
        """pop an element based on Priority time"""
        return self.__queue.get()

    def is_event_type_in_queue(
            self, event_type: Type['event_module.Event'],
            time: Optional[float] = None, owner: Optional[Any] = None) -> bool:
        is_in_queue = False
        for event in self.__queue.queue:
            if owner is not None \
                    and isinstance(event, event_module.ActionEvent) \
                    and event.state_machine.owner == owner \
                    and self.__is_event_looked_for(event, event_type, time):
                is_in_queue = True
                break
            elif owner is None \
                    and self.__is_event_looked_for(event, event_type, time):
                is_in_queue = True
                break

        return is_in_queue

    def cancel_event_type(self, event_type: Type['event_module.Event'],
                          time: Optional[float] = None,
                          owner: Optional[Any] = None) -> None:
        events_to_be_cancelled = []
        for event in self.__queue.queue:
            if owner is not None \
                    and isinstance(event, event_module.ActionEvent) \
                    and event.state_machine.owner == owner \
                    and self.__is_event_looked_for(event, event_type, time):
                events_to_be_cancelled.append(event)
            elif owner is None \
                    and self.__is_event_looked_for(event, event_type, time):
                events_to_be_cancelled.append(event)

        self.cancel_events(events_to_be_cancelled)

    def cancel_events(self, events: list['event_module.Event']) -> None:
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
