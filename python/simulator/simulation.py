import sys

# sys.path.append('C:/Users/asmam/PycharmProjects/SimulatorMultimodal')
from event_queue import EventQueue
from python.optimization.optimization import GreedyOptimization, BusOptimization
from python.simulator.passenger_event_process import PassengerRelease
from vehicle_event_process import *

from vehicle import *
from request import *
from read_data import *
from status import *
from environment import *
from event import *


def init_simulation(queue, request_data_list, vehicle_data_list):
    for vehicle_data_dict in vehicle_data_list:
        VehicleReady(queue, vehicle_data_dict).add_to_queue()

    for request_data_dict in request_data_list:
        PassengerRelease(queue, request_data_dict).add_to_queue()


def simulate(env, queue, request_data_list, vehicle_data_list):
    # init_simulation(env.get_requests(), env.get_vehicles(), queue, request_data_list, vehicle_data_list)
    init_simulation(queue, request_data_list, vehicle_data_list)

    # main loop of the simulation
    while not queue.is_empty():
        print_environment(queue.env)

        event_time, current_event = queue.pop()

        # Patrick: When should we update env.current_time?
        env.current_time = event_time

        print("current_time={} | event_time={} | current_event={}".format(env.current_time, event_time, current_event))
        process_event = current_event.process(env)
        print("process_event: {}".format(process_event))

    print("\n***************\nEND OF SIMULATION\n***************")
    print_environment(queue.env)


def print_environment(env):
    print("\n***************\nENVIRONMENT")
    print("env.current_time={}".format(env.current_time))
    print("OptimizationStatus: {}".format(env.optimization.status))
    print("Vehicles:")
    for vehicle in env.get_vehicles():
        # print(vehicle)
        print(" --id: {}, status: {}".format(vehicle.id, vehicle.route.status, vehicle.route.current_stop))
        print("  --previous_stops:")
        for stop in vehicle.route.previous_stops:
            print("   --{}: {}".format(stop.location, stop))
        print("  --current_stop:")
        if vehicle.route.current_stop is not None:
            print("   --{}: {}".format(vehicle.route.current_stop.location, vehicle.route.current_stop))
        else:
            print("   --{}".format(vehicle.route.current_stop))
        print("  --next_stops:")
        for stop in vehicle.route.next_stops:
            print("   --{}: {}".format(stop.location, stop))
    print("Requests:")
    for request in env.get_requests():
        print(request)
    print("***************\n")


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

    request_data_list = read_file_bus_requests(requests_file_path)
    vehicle_data_list = read_file_bus_vehicles(vehicles_file_path)

    return env, request_data_list, vehicle_data_list


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
        env, request_data_list, vehicle_data_list = create_bus_environment_from_files(requests_file_path, vehicles_file_path)
    else:
        raise ValueError("Either 3 or 4 arguments must be passed to the program!")

    eq = EventQueue(env)
    simulate(env, eq, request_data_list, vehicle_data_list)


if __name__ == '__main__':
    main(sys.argv)
