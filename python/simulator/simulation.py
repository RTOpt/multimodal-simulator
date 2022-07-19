import sys

# sys.path.append('C:/Users/asmam/PycharmProjects/SimulatorMultimodal')
from event_queue import EventQueue
from python.optimization.optimization import GreedyOptimization, BusOptimization
from vehicle_event_process import *

from vehicle import *
from request import *
from read_data import *
from status import *
from environment import *
from event import *


def init_simulation(requests, vehicles, queue):

    for req in requests:
        PassengerRelease(req, queue).add_to_queue()

    for veh in vehicles:
        VehicleReady(veh, queue).add_to_queue()




def simulate(env, queue):
    init_simulation(env.get_requests(), env.get_vehicles(), queue)

    # main loop of the simulation
    while not queue.is_empty():
        print_environment(queue.env)

        event_time, current_event = queue.pop()

        # Patrick: When should we update env.current_time?
        env.current_time = event_time

        print("current_time={} | event_time={} | current_event={}".format(env.current_time, event_time, current_event))
        process_event = current_event.process(env)
        print("process_event: {}".format(process_event))


def print_environment(env):
    print("env.current_time={}".format(env.current_time))
    print("Vehicles:")
    for vehicle in env.get_vehicles():
        print(vehicle)
    print("Requests:")
    for request in env.get_requests():
        print(request)

class Visualization(object):
    """plots solutions"""


def display_instance(instances):
    for i in instances:
        print(i)


def create_environment_from_files(nodes_file_path, requests_file_path, vehicles_file_path):
    nodes = read_file_nodes(nodes_file_path)
    g = create_graph(nodes)

    opt = GreedyOptimization()
    env = Environment(opt, g)

    read_file_bus_requests(requests_file_path, env)
    read_file_bus_vehicles(vehicles_file_path, env)

    return env


def create_bus_environment_from_files(requests_file_path, vehicles_file_path):

    opt = BusOptimization()
    env = Environment(opt)

    read_file_bus_requests(requests_file_path, env)
    read_file_bus_vehicles(vehicles_file_path, env)

    return env


def main(argv):

    if len(argv) == 4:
        print("STANDARD")
        nodes_file_path = argv[1]
        requests_file_path = argv[2]
        vehicles_file_path = argv[3]
        env = create_environment_from_files(nodes_file_path, requests_file_path, vehicles_file_path)
    elif len(argv) == 3:
        print("BUS")
        requests_file_path = argv[1]
        vehicles_file_path = argv[2]
        env = create_bus_environment_from_files(requests_file_path, vehicles_file_path)
    else:
        raise ValueError("Either 3 or 4 arguments must be passed to the program!")

    eq = EventQueue(env)
    simulate(env, eq)


if __name__ == '__main__':
    main(sys.argv)
