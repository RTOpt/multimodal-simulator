from networkx.algorithms.shortest_paths.generic import shortest_path


def find_shortest_path(G, o, d):

    path = shortest_path(G, source=o, target=d, weight='length')
    #path_length = path_weight(G, path, weight='length')

    return path

def get_path(G, node1, node2):
    for node in G.nodes:
        if node.coordinates == node1:
            origin = node
        if node.coordinates == node2:
            destination = node
    path = find_shortest_path(G, origin, destination)
    #path_cost = get_manhattan_distance(node1, node2)
    return path


def optimization_algo(env):
    non_assigned_requests = env.get_non_assigned_requests()
    non_assigned_vehicles = env.get_non_assigned_vehicles()


    veh = 0
    for req in non_assigned_requests:
        if veh < len(non_assigned_vehicles)+1:
            req.assign_route(get_path(env.network, req.origin, req.destination))
            assigned_vehicle = non_assigned_vehicles[veh]
            req.assign_vehicle(assigned_vehicle)
            veh += 1

