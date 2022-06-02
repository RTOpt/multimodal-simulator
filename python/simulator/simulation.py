import sys
sys.path.append('C:/Users/asmam/PycharmProjects/SimulatorMultimodal')
from queue import PriorityQueue


from vehicle import *
from request import *
from read_data import *
from statuts import *
from environment import *
from event import *



def init_simulation(requests, vehicles, queue):

    for veh in vehicles:
        event = VehicleReady(veh, queue)
        event.add_to_queue()

    for req in requests:
        event = PassengerRelease(req, queue)
        event.add_to_queue()




def simulate(env, queue):
    init_simulation(env.get_requests(), env.get_vehicles(), queue)

    # main loop of the simulation
    while not queue.empty():
        current_event = queue.get()

        process_event = current_event.process(env)
        print(process_event)




class Visualization(object):
    """plots solutions"""
    pass


def display_instance(instances):
    for i in instances:
        print(i)


def main():
    data_path = 'C:/Users/asmam/PycharmProjects/SimulatorMultimodal/data/test/'
    nodes = read_file_nodes(data_path + 'nodes.csv')
    G = create_graph(nodes)
    env = Environment(G)

    read_file_requests(data_path+'requests.csv', env)

    read_file_vehicles(data_path+'vehicles.csv', env)


    eq = PriorityQueue()
    simulate(env, eq)




if __name__ == '__main__':
    main()



