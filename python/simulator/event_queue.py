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
        # self.queue.put((-event.time, event))
        self.__queue.put((event.time, event))
        self.__index += 1

    # pop an element based on Priority time
    def pop(self):

        return self.__queue.get()

#
# q = PriorityQueue()
# q.put((10,'Red balls'))
# q.put((8,'Pink balls'))
# q.put((5,'White balls'))
# q.put((4,'Green balls'))
# while not q.empty():
#     item = q.get()
#     print(item)
