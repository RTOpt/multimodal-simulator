from queue import PriorityQueue


class EventQueue(object):
    def __init__(self, env):
        self.__queue = PriorityQueue()

        self.__index = 0

        self.env = env

    def is_empty(self):
        """check if the queue is empty"""
        return self.__queue.empty()

    def put(self, event):
        """add an element in the queue"""
        # self.__queue.put((-event.time, event))
        self.__queue.put((event.time, self.__index, event))
        self.__index += 1

    def pop(self):
        """pop an element based on Priority time"""
        return self.__queue.get()
