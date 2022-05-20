import sys
sys.path.append('C:/Users/asmam/PycharmProjects/SNCF_TAD/optimization')

from statuts import *
from network import *


class Request(object):
    """The ``Request`` class mostly serves as a structure for storing basic
       information about the request
       Attributes:
       ----------
       requestId: int
            unique id for each request
       status: category
            Request status : {PENDING:1, PICKING:2, ONBOARD:3, COMPLET:4}
       origin: tuple of floats (x,y)
            GPS coordinates of the origin point of the request.
       destination:  tuple of floats (x,y)
            GPS coordinates of the destination point of the request.
       travel_duration: float
            Travel time between the origin and destination
       travel_distance: float
            Travel distance between the origin and destination
       nb_passengers: int
            Number of passengers of the request.
       ready_time: float
            time at which the request has to be picked up.
       due_time float
            time at which the request has to be dropped off.
       release_time float
            time and Time at which the request is appeared in the system.
       """

    def __init__(self, req_id, origin, destination, nb_passengers, ready_time, due_time, release_time):
        self.req_id = req_id
        self.origin = origin
        self.destination = destination
        self.nb_passengers = nb_passengers
        self.ready_time = ready_time
        self.due_time = due_time
        self.release_time = release_time
        #self.path = get_shortest_path(origin, destination)
        #elf.travel_duration = travel_duration
        self.travel_distance = get_manhattan_distance(origin, destination)

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)




class Trip(Request):
    """The ``Trip`` class serves as a structure for storing basic
        information about the trips. This class inherits from Request class
        Properties
        ----------
        affected_vehicle:int
            Id of affected vehicle to run the request.
        origin_affected_request: tuple of floats (x,y)
            GPS coordinates of the origin point of the affected request.
        destination_affected_request: tuple of floats (x,y)
            GPS coordinates of the destination point of the affected request.
    """
    def __init__(self):
        self.affected_vehicle = 0
        self.origin_affected_request = 0
        self.destination_affected_request = 0



