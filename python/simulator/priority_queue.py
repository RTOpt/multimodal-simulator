import heapq

class PriorityQueue(object):
    def __init__(self):
        self.queue = []
        self.time = 0
        self._index = 0

    # check if the queue is empty
    def is_empty(self):
        return len(self.queue) == 0

    # add an element in the queue
    def put(self, event, priority):
        heapq.heappush(self.queue, (-priority, self._index, event))
        self._index += 1

    # pop an element based on Priority time
    def pop(self):
        return heapq.heappop(self.queue)[-1]
