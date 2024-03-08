import functools
import logging
import time

logger = logging.getLogger(__name__)


@functools.total_ordering
class Event(object):
    """An event with event_number occurs at a specific time ``event_time``
    and involves a specific event type ``event_type``. Comparing two events
    amounts to figuring out which event occurs first """

    MAX_PRIORITY = 1000
    VERY_LOW_PRIORITY = 7
    LOW_PRIORITY = 6
    STANDARD_PRIORITY = 5
    HIGH_PRIORITY = 4
    MAX_DELTA_TIME = 7 * 24 * 3600

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
        elif event_time > self.MAX_DELTA_TIME:
            logger.warning(
                "WARNING: {}: event_time ({}) is much larger than "
                "current_time ({})".format(self.name, event_time,
                                           self.queue.env.current_time))
        else:
            self.__time = event_time

        if event_priority < 0:
            raise ValueError("The parameter event_priority must be positive!")

        if event_priority > self.MAX_PRIORITY:
            event_priority = self.MAX_PRIORITY
            logger.warning(
                "event_priority ({}) must be smaller than MAX_PRIORITY ({})"
                .format(event_priority, self.MAX_PRIORITY))

        self.__priority = 1 - 1 / (1 + event_priority)

        self.__cancelled = False

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

    @property
    def cancelled(self):
        return self.__cancelled

    @cancelled.setter
    def cancelled(self, cancelled):
        self.__cancelled = cancelled

    def process(self, env):

        if not self.cancelled:
            return_message = self._process(env)
        else:
            return_message = "The event was cancelled."

        return return_message

    def _process(self, env):
        raise NotImplementedError('_process of {} not implemented'.
                                  format(self.__class__.__name__))

    def __lt__(self, other):
        """ Returns True if self.time < other.time or self.time == other.time
        and self.priority < other.priority"""
        result = False
        if self.time < other.time:
            result = True
        elif self.time == other.time and self.priority < other.priority:
            result = True

        return result

    def __eq__(self, other):
        """ Returns True if self.time + self.priority
        == other.time + other.priority"""
        # return self.time + self.priority == other.time + other.priority
        result = False
        if self.time == other.time and self.priority == other.priority:
            result = True

        return result

    def add_to_queue(self):
        self.queue.put(self)


class ActionEvent(Event):

    def __init__(self, event_name, queue, event_time=None,
                 event_priority=Event.STANDARD_PRIORITY, state_machine=None):
        super().__init__(event_name, queue, event_time, event_priority)

        if state_machine is not None \
                and self.__class__.__name__ not in state_machine.transitions:
            raise ValueError("A transition triggered by event {} must "
                             "exist!".format(self.__class__.__name__))

        self.__state_machine = state_machine

        self.__cancelled = False

    @property
    def state_machine(self):
        return self.__state_machine

    def process(self, env):

        if not self.cancelled:
            if self.__state_machine is not None:
                self.__state_machine.next_state(self.__class__, env)
            return_message = self._process(env)
        else:
            return_message = "The event was cancelled."

        return return_message


class TimeSyncEvent(Event):

    def __init__(self, queue, event_time, speed=None, max_waiting_time=None,
                 event_priority=None, event_name=None):
        if event_priority is None:
            event_priority = self.MAX_PRIORITY
        if event_name is None:
            event_name = "TimeSyncEvent"
        super().__init__(event_name, queue, event_time, event_priority)

        if speed is not None:
            current_time = queue.env.current_time
            self.__event_timestamp = time.time() \
                                     + (event_time - current_time) / speed
        elif max_waiting_time is not None:
            self.__event_timestamp = time.time() + max_waiting_time
        else:
            raise ValueError("Either the parameter 'speed' or the parameter "
                             "'max_waiting_time' must be different from None.")

        self._waiting_time = None

    def process(self, env):
        current_timestamp = time.time()
        self._waiting_time = self.__event_timestamp - current_timestamp \
            if self.__event_timestamp - current_timestamp > 0 else 0
        self._synchronize()
        self._process(env)

    def _synchronize(self):
        if self._waiting_time > 0:
            time.sleep(self._waiting_time)

    def _process(self, env):
        return str(self._waiting_time)


class RecurrentTimeSyncEvent(TimeSyncEvent):
    def __init__(self, queue, event_time, speed,
                 time_step, event_priority=None):
        super().__init__(queue, event_time, speed=speed,
                         event_priority=event_priority,
                         event_name="RecurrentTimeSyncEvent")

        self.__event_time = event_time
        self.__queue = queue
        self.__speed = speed
        self.__time_step = time_step
        self.__event_priority = event_priority

    def _process(self, env):
        if not self.__queue.is_empty():
            RecurrentTimeSyncEvent(
                self.__queue, self.__event_time + self.__time_step,
                self.__speed,
                self.__time_step, self.__event_priority).add_to_queue()

        return super()._process(env)


class PauseEvent(Event):
    def __init__(self, queue, event_time, event_priority=None):
        if event_priority is None:
            event_priority = self.MAX_PRIORITY
        super().__init__("PauseEvent", queue, event_time, event_priority)

    def _process(self, env):
        return "Simulation paused"


class ResumeEvent(Event):
    def __init__(self, queue, event_time, event_priority=None):
        if event_priority is None:
            event_priority = self.MAX_PRIORITY
        super().__init__("ResumeEvent", queue, event_time, event_priority)

    def _process(self, env):
        return "Simulation resumed"
