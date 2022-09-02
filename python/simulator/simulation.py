import sys
sys.path.append('C:/Users/asmam/PycharmProjects/SimulatorMultimodal')

from event_queue import EventQueue
from python.optimization.optimization import ShuttleOptimization, BusOptimization
from python.simulator.passenger_event_process import PassengerRelease
from vehicle_event_process import *

from read_data import *
from environment import *


def init_simulation(queue, request_data_list, vehicle_data_list):
    for vehicle_data_dict in vehicle_data_list:
        VehicleReady(vehicle_data_dict, queue).add_to_queue()

    for request_data_dict in request_data_list:
        PassengerRelease(request_data_dict, queue).add_to_queue()


def simulate(env, queue, request_data_list, vehicle_data_list):
    init_simulation(queue, request_data_list, vehicle_data_list)

    # main loop of the simulation
    while not queue.is_empty():
        print_environment(queue.env)

        event_time, event_index, current_event = queue.pop()

        # Patrick: Should we update env.current_time here?
        env.current_time = event_time

        print("current_time={} | event_time={} | current_event={}".format(env.current_time, event_time, current_event))
        process_event = current_event.process(env)
        print("process_event: {}".format(process_event))

    print("\n***************\nEND OF SIMULATION\n***************")
    print_environment(queue.env)


def print_environment_status(env):
    print("\n***************\nENVIRONMENT STATUS")
    print("env.current_time={}".format(env.current_time))
    print("OptimizationStatus: {}".format(env.optimization.status))
    print("Vehicles:")
    for vehicle in env.get_vehicles():
        print("{}: {}".format(vehicle.id, vehicle.route.status))
    print("Requests:")
    for request in env.get_requests():
        print("{}: {}".format(request.req_id, request.status))
    print("***************\n")


def print_environment(env):
    print("\n***************\nENVIRONMENT STATUS")
    print("env.current_time={}".format(env.current_time))
    print("OptimizationStatus: {}".format(env.optimization.status))
    print("Vehicles:")
    for veh in env.get_vehicles():
        assigned_requests_id = [req.req_id for req in veh.route.assigned_requests]
        print("{}: status: {}, start_time: {}, assigned_requests: {}".format(veh.id, veh.route.status, veh.start_time,
                                                                             assigned_requests_id))
        print("  --previous_stops:")
        for stop in veh.route.previous_stops:
            print("   --{}: {}".format(stop.location, stop))
        print("  --current_stop:")
        if veh.route.current_stop is not None:
            print("   --{}: {}".format(veh.route.current_stop.location, veh.route.current_stop))
        else:
            print("   --{}".format(veh.route.current_stop))
        print("  --next_stops:")
        for stop in veh.route.next_stops:
            print("   --{}: {}".format(stop.location, stop))
    print("Requests:")
    for req in env.get_requests():
        assigned_vehicle_id = req.assigned_vehicle.id if req.assigned_vehicle is not None else None
        print("{}: status: {}, OD: ({},{}), release: {}, ready: {}, due: {}, assigned_vehicle: {}".
              format(req.req_id, req.status, req.origin, req.destination, req.release_time, req.ready_time,
                     req.due_time,
                     assigned_vehicle_id))
    print("***************\n")


class Visualization(object):
    """plots solutions"""


def display_instance(instances):
    for i in instances:
        print(i)


def create_environment_from_files(nodes_file_path, requests_file_path, vehicles_file_path):
    nodes = read_file_nodes(nodes_file_path)
    g = create_graph(nodes)

    opt = ShuttleOptimization()
    env = Environment(opt, g)

    request_data_list = read_file_requests(requests_file_path)
    vehicle_data_list = read_file_vehicles(vehicles_file_path)

    return env, request_data_list, vehicle_data_list


def create_bus_environment_from_files(requests_file_path, vehicles_file_path):
    opt = BusOptimization()
    env = Environment(opt)

    request_data_list = read_file_bus_requests(requests_file_path)
    vehicle_data_list = read_file_bus_vehicles(vehicles_file_path)

    return env, request_data_list, vehicle_data_list


def main(argv):
    if len(argv) == 4:
        # 3 arguments have to be passed: the relative paths to the requests, the vehicles and the nodes.
        # For example: ../../data/test/requests.csv ../../data/test/vehicles.csv ../../data/test/nodes.csv
        print("SHUTTLE")
        requests_file_path = argv[1]
        vehicles_file_path = argv[2]
        nodes_file_path = argv[3]
        env, request_data_list, vehicle_data_list = create_environment_from_files(nodes_file_path, requests_file_path,
                                                                                  vehicles_file_path)
    elif len(argv) == 3:
        print("BUS")
        # 2 arguments have to be passed: the relative paths to the requests and the vehicles.
        # For example: ../../data/bus_test/requests_v1.csv ../../data/bus_test/vehicles_v1.csv
        requests_file_path = argv[1]
        vehicles_file_path = argv[2]
        env, request_data_list, vehicle_data_list = create_bus_environment_from_files(requests_file_path,
                                                                                        vehicles_file_path)
    else:
        raise ValueError("Either 3 or 4 arguments must be passed to the program!")

    eq = EventQueue(env)
    simulate(env, eq, request_data_list, vehicle_data_list)


if __name__ == '__main__':
    main(sys.argv)
