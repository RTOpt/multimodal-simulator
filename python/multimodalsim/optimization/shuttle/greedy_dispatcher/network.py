class Node(object):
    def __init__(self, node_id, coordinates):
        self.id = node_id
        self.coordinates = coordinates
        self.in_arcs = []
        self._out_arcs = []

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def get_node_id(self):
        return self.id

    def get_coordinates(self):
        return self.coordinates
