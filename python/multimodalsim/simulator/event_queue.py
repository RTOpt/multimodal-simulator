from queue import PriorityQueue


class EventQueue(object):
    # Why not inherit EventQueue directly from PriorityQueue?
    def __init__(self, env):
        self.__queue = PriorityQueue()

        # How will self.__index be used?
        self.__index = 0

        self.env = env

    # check if the queue is empty
    def is_empty(self):
        return self.__queue.empty()

    # add an element in the queue
    def put(self, event):

        # Why -event.time?
        # self.__queue.put((-event.time, event))
        self.__queue.put((event.time, self.__index, event))
        self.__index += 1

    # pop an element based on Priority time
    def pop(self):
        return self.__queue.get()
