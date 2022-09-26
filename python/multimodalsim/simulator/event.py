import logging

logger = logging.getLogger(__name__)


class Event(object):
    """An event with event_number occurs at a specific time ``event_time`` and involves a specific
        event type ``event_type``. Comparing two events amounts to figuring out which event occurs first """

    def __init__(self, event_name, queue, event_time=None):
        self.name = event_name
        self.queue = queue
        self.time = event_time

        if event_time is None:
            self.time = queue.env.current_time
        elif event_time < queue.env.current_time:
            self.time = queue.env.current_time
            logger.warning(
                "WARNING: {}: event_time ({}) is smaller than current_time ({})".format(event_name, event_time,
                                                                                        queue.env.current_time))

    def process(self, env):
        raise NotImplementedError('Process not implemented')

    def __lt__(self, other):
        """ Returns True if self.event_time < other.event_time"""
        return self.time < other.time

    def add_to_queue(self):
        self.queue.put(self)

    def get_event(self):
        """Gets the first event in the event list"""
        event = self.queue.get()
        return event

    def get_name(self):
        """ returns event name"""
        return self.name

    def get_time(self):
        """ returns event time"""
        return self.time
