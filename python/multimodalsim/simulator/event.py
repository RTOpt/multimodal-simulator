import logging

logger = logging.getLogger(__name__)


class Event(object):
    """An event with event_number occurs at a specific time ``event_time`` and involves a specific
        event type ``event_type``. Comparing two events amounts to figuring out which event occurs first """

    def __init__(self, event_name, queue, event_time=None):
        self.__name = event_name
        self.__queue = queue

        if event_time is None:
            self.__time = self.queue.env.current_time
        elif event_time < self.queue.env.current_time:
            self.__time = self.queue.env.current_time
            logger.warning(
                "WARNING: {}: event_time ({}) is smaller than current_time ({})".format(self.name, event_time,
                                                                                        self.queue.env.current_time))
        else:
            self.__time = event_time

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

    def process(self, env):
        raise NotImplementedError('Process not implemented')

    def __lt__(self, other):
        """ Returns True if self.time < other.time"""
        return self.time < other.time

    def add_to_queue(self):
        self.queue.put(self)

    # def get_event(self):
    #     """Gets the first event in the event list"""
    #     event = self.queue.get()
    #     return event
    #
    # def get_name(self):
    #     """ returns event name"""
    #     return self.name
    #
    # def get_time(self):
    #     """ returns event time"""
    #     return self.time
