import functools
import logging

logger = logging.getLogger(__name__)


@functools.total_ordering
class Event(object):
    """An event with event_number occurs at a specific time ``event_time``
    and involves a specific event type ``event_type``. Comparing two events
    amounts to figuring out which event occurs first """

    def __init__(self, event_name, queue, event_time=None, event_priority=5,
                 index=None):
        self.__name = event_name
        self.__queue = queue
        self.__index = index

        if event_time is None:
            self.__time = self.queue.env.current_time
        elif event_time < self.queue.env.current_time:
            self.__time = self.queue.env.current_time
            logger.warning(
                "WARNING: {}: event_time ({}) is smaller than current_time ("
                "{})".format(self.name, event_time,
                             self.queue.env.current_time))
        else:
            self.__time = event_time

        if event_priority < 0:
            raise ValueError("The parameter event_priority must be positive!")

        self.__priority = 1 - 1 / (1 + event_priority)

    @property
    def name(self):
        return self.__name

    @property
    def queue(self):
        return self.__queue

    @property
    def time(self):
        return self.__time

    @time.setter
    def time(self, time):
        self.__time = time

    @property
    def priority(self):
        return self.__priority

    @property
    def index(self):
        return self.__index

    @index.setter
    def index(self, index):
        self.__index = index

    def process(self, env):
        return self._process(env)

    def _process(self, env):
        raise NotImplementedError('_process of {} not implemented'.
                                  format(self.__class__.__name__))

    def __lt__(self, other):
        """ Returns True if self.time + self.priority
        < other.time + other.priority"""
        return self.time + self.priority < other.time + other.priority

    def __eq__(self, other):
        """ Returns True if self.time + self.priority
        == other.time + other.priority"""
        return self.time + self.priority == other.time + other.priority

    def add_to_queue(self):
        self.queue.put(self)


class ActionEvent(Event):

    def __init__(self, event_name, queue, event_time=None, event_priority=5,
                 state_machine=None):
        super().__init__(event_name, queue, event_time, event_priority)

        if state_machine is not None \
                and self.__class__.__name__ not in state_machine.transitions:
            raise ValueError("A transition triggered by event {} must "
                             "exist!".format(self.__class__.__name__))

        self.__state_machine = state_machine

    def process(self, env):

        if self.__state_machine is not None:
            self.__state_machine.next_state(self.__class__)

        return self._process(env)

    def _process(self, env):
        return super()._process()
