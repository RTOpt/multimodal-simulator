import heapq

class PriorityQueue(object):
    def __init__(self):
        self.queue = PriorityQueue()
        self.time = 0
        self._index = 0

    # check if the queue is empty
    def is_empty(self):
        return len(self.queue) == 0

    # add an element in the queue
    def put(self, event):
        self.queue.put((-event.time, event))
        self._index += 1

    # pop an element based on Priority time
    def pop(self):
        return self.queue.get()


# from queue import priorityQueue
# q = PriorityQueue()
# q.put((10,'Red balls'))
# q.put((8,'Pink balls'))
# q.put((5,'White balls'))
# q.put((4,'Green balls'))
# while not q.empty():
#     item = q.get()
#     print(item)
