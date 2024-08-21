from graph_constructor import *
# This file contains all unit tests for classes Graph_Node, Graph_Edge and Graph and tests all the functions in the graph constructor file


def test_graph_node():
    # Test the constructor
    node1 = Graph_Node(stop_id = 1, ad = 'd', time = 10, real_time=12, type='normal', flow = 0, level = 1, dist = 3.2, bus = 1)
    node1bis = Graph_Node(stop_id = 1, ad = 'a', time = 10, real_time=12, type='normal', flow = 0, level = 1, dist = 3.2, bus = 1)
    node2 = Graph_Node(stop_id = 2, ad = 'a', time = 15, real_time=15, type='normal', flow = 0, level = 2, dist = 4.2, bus = 2)
    assert node1.node_stop_id == 1
    assert node1.node_type == 'normal'
    assert node1.node_time == 10
    assert node1.node_transfer_time == 12
    assert node1.node_arrival_departure == 'd'
    assert node1.node_flow == 0
    assert node1.node_level == 1
    assert node1.node_dist == 3.2
    assert node1.node_bus == 1
    assert (node1 == node2) == False
    assert (node1 == node1bis) == False
    dict = {}
    dict[node1] = 1
    assert dict[node1] == 1
    node1.show_node
    print('Graph_Node constructor test passed')

def test_graph_edge():
    node1 = Graph_Node(stop_id = 1, ad = 'd', time = 10, real_time=12, type='normal', flow = 0, level = 1, dist = 3.2, bus = 1)
    node2 = Graph_Node(stop_id = 2, ad = 'a', time = 15, real_time=15, type='normal', flow = 0, level = 2, dist = 4.2, bus = 2)
    edge1 = Graph_Edge(node1, node2, weight =5, sp=1, ss=0)
    edge2 = Graph_Edge(node1, node2, sp=0, ss=1)
    assert edge1.weight == 5
    assert edge1.origin == node1
    assert edge1.destination == node2
    assert (edge1.origin ==node2) == False
    assert edge1.capacity == 10000
    assert edge1.speedup == 1
    assert edge1.skip_stop == 0
    assert edge2.weight == 0
    assert (edge1 == edge2) == False
    dict = {}
    dict[edge1] = 1
    assert dict[edge1] == 1
    edge1.show_edge

    print('Graph_Edge constructor test passed')

def test_graph():
    source = Graph_Node(stop_id = 0, ad = 'd', time = -2, real_time=0, type='normal', flow = 0, level = 0, dist = 0, bus = 1)
    target = Graph_Node(stop_id = 0, ad = 'a', time = 100, real_time=100, type='normal', flow = 0, level = 0, dist = 0, bus = 1)
    node1 = Graph_Node(stop_id = 1, ad = 'd', time = 10, real_time=12, type='normal', flow = 0, level = 1, dist = 3.2, bus = 1)
    node2 = Graph_Node(stop_id = 2, ad = 'a', time = 15, real_time=15, type='normal', flow = 0, level = 2, dist = 4.2, bus = 2)
    G = Graph('test', [source, target, node1, node2], [], source, target)
    assert G.name == 'test'
    assert G.nodes == [source, target, node1, node2]
    assert G.edges == []
    assert G.source == source
    assert G.target == target
    assert G.time_step == 20
    assert G.price == 3600
    assert G.nb_edges == 0
    assert G.nb_nodes == 4
    assert G.contains_node(node1) == True
    assert G.contains_node(node2) == True
    G.add_node(source)
    assert G.nb_nodes == 4
    G.add_edge(node1, node2, 5, 1, 0)
    G.add_edge(node1, node2)
    assert G.nb_edges == 1
    G.price = 2000
    assert G.price == 2000
    G.time_step = 10
    assert G.time_step == 10
    assert G.get_node(stop_id=0, ad='d', time=-2, type='normal') == source
    assert G.get_node(stop_id=1, ad='d', time=10, type='normal') == node1
    assert G.get_node(stop_id=2, ad='a', time=15, type='normal') == node2
    assert G.get_node(stop_id=0, ad='a', time=100, type='normal') == target
    assert G.get_node(0, 'a', -2, type='normal') == False
    G.show_graph
    print('Graph constructor test passed')

# test_graph_node()
# test_graph_edge()
# test_graph()

# Create small instance for the graph constructor 
# Create initial flows
initial_flows = {}
initial_flows['1'] = 2
initial_flows['2'] = 3
# Create bus_trips
bus_trips = {}
Stop1_1 = Stop(100, 120, LabelLocation(1), cumulative_distance=1, planned_arrival_time=100, planned_departure_time_from_origin=0)
Stop1_1.passengers_to_board_int = 1
Stop2_1 = Stop(210, 230, LabelLocation(2), cumulative_distance=2.5, planned_arrival_time=210, planned_departure_time_from_origin=0)
Stop3_1 = Stop(300, 330, LabelLocation(3), cumulative_distance=3.5, planned_arrival_time=300, planned_departure_time_from_origin=0)
bus_trips['1'] = [Stop1_1, Stop2_1, Stop3_1]
Stop1_2 = Stop(299, 320, LabelLocation(1), cumulative_distance=1, planned_arrival_time=300, planned_departure_time_from_origin=200)
Stop2_2 = Stop(410, 430, LabelLocation(2), cumulative_distance=2.5, planned_arrival_time=410, planned_departure_time_from_origin=200)
Stop2_2.passengers_to_board_int = 1
Stop3_2 = Stop(500, 530, LabelLocation(3), cumulative_distance=3.5, planned_arrival_time=500, planned_departure_time_from_origin=200)
Stop3_2.passengers_to_alight_int = 2
bus_trips['2'] = [Stop1_2, Stop2_2, Stop3_2]
# Create transfers
transfers = {}
for trip in bus_trips:
    transfers[trip] = {}
    for i in range(1,len(bus_trips[trip])+1):
        transfers[trip][i] = {}
        transfers[trip][i]['boarding'] = []
        transfers[trip][i]['alighting'] = []
transfers['1'][1]['boarding'] = [(140, 2)]
transfers['1'][2]['alighting'] = [(270, 1, 1200)]
transfers['2'][2]['boarding'] = [(479, 2)]
transfers['2'][2]['alighting'] = [(509, 2, 900)]

# Create prev_times
prev_times = {}
prev_times['1'] = 0
prev_times['2'] = 200
# Create od_dict
od_dict = {}
#Create time step and price
time_step = 2
price = 3600

# G, trip_id, bus_departures = build_graph_without_tactics(bus_trips = bus_trips, 
#                             transfers = transfers, 
#                             initial_flows = initial_flows, 
#                             prev_times = prev_times, 
#                             od_dict = od_dict, 
#                             time_step = time_step, 
#                             price = price)
# # display_graph(G, display_flows = False, name = 'Graph_Image', savepath = os.path.join('output','fixed_line','gtfs'))
# optimal_value, bus_flows, display_flows, runtime = G.build_and_solve_model_from_graph("Model_No_Tactics",
#                                                                         verbose=False,
#                                                                         out_of_bus_price= 2)
# display_graph(G, display_flows = display_flows, name = 'Graph_Image', savepath = os.path.join('output','fixed_line','gtfs'))
# max_departure_time, hold, speedup, skip_stop = extract_tactics_from_solution(bus_flows, stop_id=1, trip_id='1')
# print('Max departure time:', max_departure_time
#       , 'Hold:', hold   
#       , 'Speedup:', speedup
#       , 'Skip stop:', skip_stop)

G_with_tactics = build_graph_with_tactics(bus_trips = bus_trips, 
                            transfers = transfers, 
                            initial_flows = initial_flows, 
                            prev_times = prev_times, 
                            time_step = 2,
                            price = 3600,
                            global_speedup_factor = 1,
                            global_skip_stop_is_allowed = False,
                            od_dict  = {},
                            simu = False,
                            last_stop = 2)
# display_graph(G_with_tactics, display_flows = False, name = 'Graph_Image_Tactics', savepath = os.path.join('output','fixed_line','gtfs'))
optimal_value, bus_flows, display_flows, runtime = G_with_tactics.build_and_solve_model_from_graph("Model_Tactics",
                                                                                         verbose = False, 
                                                                                         out_of_bus_price = 2)
# for edge in [edge for edge in G_with_tactics.edges if edge.origin.node_stop_id == 2 and (edge.origin.node_bus=='2' or edge.destination.node_bus=='2')] :
#     print('stop_id',edge.origin.node_stop_id, 'time:',edge.origin.node_time, edge.origin.node_type, 'flow:',edge.origin.node_flow,'bus', edge.origin.node_bus,
#           'stop_id',edge.destination.node_stop_id, 'time:',edge.destination.node_time, edge.destination.node_type, 'flow:',edge.destination.node_flow, 'bus', edge.destination.node_bus,
#           edge.weight,
#           display_flows[edge])
display_graph(G_with_tactics, display_flows = display_flows, name = 'Graph_Image_Tactics', savepath = os.path.join('output','fixed_line','gtfs'))
max_departure_time, hold, speedup, skip_stop = extract_tactics_from_solution(bus_flows, stop_id=1, trip_id='1')
print('Max departure time:', max_departure_time
      , 'Hold:', hold   
      , 'Speedup:', speedup
      , 'Skip stop:', skip_stop)
tactics = get_all_tactics_used_in_solution(bus_flows, trip_id='1', next_trip_id='2')
print('Tactics:', tactics)