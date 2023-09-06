import itertools
import csv
from copy import deepcopy

from multimodalsim.optimization.shuttle.constraints_and_objective_function import \
    verify_all_constraints, objective_function, variables_declaration


def get_distances(G):
    # distances = [[0]*len(G.nodes) for i in range(len(G.nodes))]
    distances = {}
    for node1, node2, data in G.edges(data=True):
        if node1 not in distances:
            distances[node1] = {}
        distances[node1][node2] = data['length']

    for node in G.nodes():
        distances[node][node] = 0

    return distances


def get_durations(G):
    # durations = [[0] * len(G.nodes) for i in range(len(G.nodes))]
    durations = {}
    for node1, node2, data in G.edges(data=True):
        if node1 not in durations:
            durations[node1] = {}
        durations[node1][node2] = data['cost']

    for node in G.nodes():
        durations[node][node] = 0

    return durations


def copy_solution(X, Y, U, W, R):
    # X_org = {key: list([list(j) for j in i]) for key, i in X.items()}
    X_org = X.copy()

    # Y_org = {key: list(i) for key, i in Y.items()}
    Y_org = Y.copy()

    # U_org = {key: list(i) for key, i in U.items()}
    U_org = U.copy()

    # W_org = {key: list(i) for key, i in W.items()}
    W_org = W.copy()

    # R_org = {key: i for key, i in R.items()}
    R_org = R.copy()

    return X_org, Y_org, U_org, W_org, R_org


def get_routes_dict(X, V, K):
    """ Function to get routes as a dict using the data in matrices """
    routes_dict = {}
    hub_id = '0'

    for f_k in K:
        current_pos = hub_id
        routes_dict[f_k.id] = []
        while True:
            # if len(routes_dict[f_k.id]) == 0 or routes_dict[f_k.id][-1] != current_pos:
            routes_dict[f_k.id].append(current_pos)
            for f_j in V:
                if X[f_k.id][current_pos][f_j]:
                    current_pos = f_j
                    break

            if current_pos == hub_id:
                if len(routes_dict[f_k.id]) > 1:
                    routes_dict[f_k.id].append(current_pos)
                break

    return routes_dict


def add_vertex(G, new_vertex, preceding_vertex, vehicle, vehicle_path, X, Y, U,
               W, R, d, t, P, D, q):
    """ Function: add vertex to a path """
    # find the index of the preceding vertex in the vehicle path
    preceding_vertex_index = vehicle_path.index(preceding_vertex)
    # find the following vertex in the path
    following_vertex = vehicle_path[preceding_vertex_index + 1]
    if preceding_vertex_index > len(vehicle_path) - 2:
        # the preceding vertex shouldn't be the last element in the path
        return False

    if len(vehicle_path) < 3:
        # the path should have at least one vertex other than the depot
        return False

    # Update X
    X[vehicle][preceding_vertex][following_vertex] = False
    X[vehicle][preceding_vertex][new_vertex] = True
    X[vehicle][new_vertex][following_vertex] = True

    # Update Y
    Y[vehicle][new_vertex] = True

    # Update U
    U[vehicle][new_vertex] = U[vehicle][preceding_vertex] + d[
        preceding_vertex] + t[preceding_vertex][new_vertex]

    for f_i in range(preceding_vertex_index + 1, len(vehicle_path) - 1):
        U[vehicle][f_i] += t[preceding_vertex][new_vertex] + d[new_vertex] + \
                           t[new_vertex][following_vertex] \
                           - t[preceding_vertex][following_vertex]

    U[vehicle][len(G.nodes)] += t[preceding_vertex][new_vertex] + d[
        new_vertex] + t[new_vertex][following_vertex] \
                                - t[preceding_vertex][following_vertex]

    # Update R
    # for vertices other than the new one
    for f_i in range(1, len(vehicle_path) - 1):
        if (f_i <= preceding_vertex_index and vehicle_path[f_i] in [
            req.destination.label for req in P]) \
                or (f_i > preceding_vertex_index and vehicle_path[f_i] in D):
            R[vehicle_path[f_i]] += t[preceding_vertex][new_vertex] + d[
                new_vertex] + t[new_vertex][following_vertex] \
                                    - t[preceding_vertex][following_vertex]

    # update R for the new vertex
    if new_vertex in [req.origin.label for req in D]:
        # TODO  : check if the travel time R include the service time of i ? " if so, then you need to add it here"
        R[new_vertex] = U[vehicle][preceding_vertex] + d[preceding_vertex] + \
                        t[preceding_vertex][new_vertex]

    if new_vertex in [req.destination.label for req in P]:
        # TODO: check if the travel time R include the service time of i ? " if so, then you need to delete it from here"

        R[new_vertex] = U[vehicle][len(G.nodes)] - U[vehicle][new_vertex] - d[
            new_vertex]

    # Update W
    if new_vertex in [req.destination.label for req in P]:
        W[vehicle][new_vertex] = W[vehicle][preceding_vertex] + q[new_vertex]
        for f_i in range(preceding_vertex_index + 1, len(vehicle_path) - 1):
            W[vehicle][vehicle_path[f_i]] += q[new_vertex]

    if new_vertex in [req.origin.label for req in D]:
        W[vehicle][new_vertex] = W[vehicle][preceding_vertex]
        for f_i in range(preceding_vertex_index + 1):
            W[vehicle][vehicle_path[f_i]] += -q[new_vertex]

    vehicle_path.insert(preceding_vertex_index + 1, new_vertex)

    return vehicle_path


def nearest_not_served_request(source, potential_not_served_requests, G):
    """ Function: nearest not served client """
    if len(potential_not_served_requests) == 0:
        return False

    nearest = next(iter(potential_not_served_requests))
    if nearest.origin.label in source:
        distance = \
        G[nearest.destination.label][source[0]][
            'length']
        nearest_vertex = nearest.destination.label
    else:
        distance = G[nearest.origin.label][source[0]][
            'length']
        nearest_vertex = nearest.origin.label
    for f_i in potential_not_served_requests:
        if f_i.origin.label in source:
            distance_source_f_i = \
            G[f_i.destination.label][source[0]][
                'length']
            nearest_vertex_f_i = f_i.destination.label
        else:
            distance_source_f_i = \
            G[f_i.origin.label][source[0]]['length']
            nearest_vertex_f_i = f_i.origin.label

        if distance_source_f_i < distance:
            nearest = f_i
            distance = distance_source_f_i
            nearest_vertex = nearest_vertex_f_i

    return nearest, distance, nearest_vertex


def save_current_solution(X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org):
    """ save current solution """

    # X_org, Y_org, U_org, W_org, R_org = copy_solution(X, Y, U, W, R)
    # for s_k in range(len(X)):
    #     for s_i in range(len(X[s_k])):
    #         for s_j in range(len(X[s_k][s_i])):
    #             X_org[s_k][s_i][s_j] = X[s_k][s_i][s_j]
    X_org = X.copy()

    # for s_k in range(len(Y)):
    #     for s_i in range(len(Y[s_k])):
    #         Y_org[s_k][s_i] = Y[s_k][s_i]
    Y_org = Y.copy()

    # for s_k in range(len(U)):
    #     for s_i in range(len(U[s_k])):
    #         U_org[s_k][s_i] = U[s_k][s_i]
    U_org = U.copy()

    # for s_k in range(len(W)):
    #     for s_i in range(len(W[s_k])):
    #         W_org[s_k][s_i] = W[s_k][s_i]
    W_org = W.copy()

    for s_i in R.keys():
        R_org[s_i] = R[s_i]

    return X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org


def back_to_previous_solution(X, Y, U, W, R):
    """ Function: retrieve previous solution """

    # X_list = list(X.values())
    # Y_list = list(Y.values())
    # U_list = list(U.values())
    # W_list = list(W.values())

    X_org, Y_org, U_org, W_org, R_org = copy_solution(X, Y, U, W, R)
    # for s_k in range(len(X)):
    #     for s_i in range(len(X[s_k])):
    #         for s_j in range(len(X[s_k][s_i])):
    #             X[s_k][s_i][s_j] = X_org[s_k][s_i][s_j]
    X = X_org.copy()

    # for s_k in range(len(Y)):
    #     for s_i in range(len(Y[s_k])):
    #         Y[s_k][s_i] = Y_org[s_k][s_i]
    Y = Y_org.copy()

    # for s_k in range(len(U)):
    #     for s_i in range(len(U[s_k])):
    #         U[s_k][s_i] = U_org[s_k][s_i]
    U = U_org.copy()

    # for s_k in range(len(W)):
    #     for s_i in range(len(W[s_k])):
    #         W[s_k][s_i] = W_org[s_k][s_i]
    W = W_org.copy()

    for s_i in R.keys():
        R_org[s_i] = R[s_i]

    return X, Y, U, W, R


def delete_route(vehicle, route_, X, Y, U, W, R, V):
    """ Function: delete route from the solution """
    if len(route_) < 3:
        return False

    # modify X
    for f_i in range(len(X[vehicle])):
        for f_j in range(len(X[vehicle])):
            X[vehicle][f_i][f_j] = False

    # modify Y and R
    for f_v in route_[1:-1]:
        Y[vehicle][f_v] = False
        R[f_v] = 0

    # modify W and U
    for f_v in route_[:-1]:
        W[vehicle][f_v] = 0
        U[vehicle][f_v] = -1

    U[vehicle][len(V)] = -1

    return X, Y, U, W, R


def add_route(G, vehicle, route_, X, Y, U, W, R, d, t, P, D, q):
    """ Function: add route to the solution """
    if len(route_) < 3:
        return False

    # add the first vertex
    first_client = route_[1]
    Y[vehicle][first_client] = True
    X[vehicle][0][first_client] = True
    X[vehicle][first_client][0] = True
    U[vehicle][0] = 0
    U[vehicle][first_client] = t[0][first_client]
    U[vehicle][len(G.nodes)] = t[0][first_client] + d[first_client] + \
                               t[first_client][0]

    if first_client in [req.destination.label for req in P]:
        # TODO  : check if the travel time R include the service time of i ? " if so, then you need to add it here"
        R[first_client] = t[first_client][0]
        W[vehicle][first_client] = q[first_client]

    if first_client in [req.origin.label for req in D]:
        # TODO  : check if the travel time R include the service time of i ? " if so, then you need to add it here"
        R[first_client] = t[0][first_client]
        W[vehicle][0] = - q[first_client]
        W[vehicle][first_client] = 0

    # add the remaining vertices
    pre_v = first_client
    built_route = [0, first_client, 0]

    for f_v in route_[2:-1]:
        built_route = add_vertex(G, f_v, pre_v, vehicle, built_route, X, Y, U,
                                 W, R, d, t, P, D, q)
        pre_v = f_v

    return X, Y, U, W, R


def change_route(G, vehicle, previous_route, new_route_, X, Y, U, W, R, d, t,
                 P, D, q):
    """ Function: change vehicle route """
    X, Y, U, W, R = delete_route(vehicle, previous_route, X, Y, U, W, R,
                                 G.nodes)
    X, Y, U, W, R = add_route(G, vehicle, new_route_, X, Y, U, W, R, d, t, P,
                              D, q)

    return X, Y, U, W, R


def set_initial_solution(G, V_not_served, K, X, Y, U, W, R, distances, d, t,
                         V_p, P, D, q, T, max_travel_time):
    """
    define Initial possible solution:
        1- save the previous state
        2- assign the k nearest vertices from the depot to the list of the vehicles
        3- assign each vertex for one vehicle
        4- consider that the k nearest vertices will verify
        5- assign a vehicle for each one
        6- consider the other case where there is some constraints not valid
    """

    X_org, Y_org, U_org, W_org, R_org = copy_solution(X, Y, U, W, R)

    # find the k nearest vertices
    nearest_k_vertices = []
    potential_not_served_requests = deepcopy(V_not_served)
    for veh in K:
        if len(potential_not_served_requests) > 0:
            temp_dict = {}
            temp_dict['vehicle'] = veh
            temp_dict['assigned_requests'] = []
            temp_dict['next_stops'] = []
            # or len(potential_not_served_requests) == 0
            if len(nearest_k_vertices) < len(K):
                nearest_request, distance, nearest_vertex = \
                    nearest_not_served_request([
                                                   veh.start_stop.location.label],
                                               potential_not_served_requests,
                                               G)
                temp_dict['assigned_requests'].append(nearest_request)
                temp_dict['next_stops'].append(nearest_vertex)
                potential_not_served_requests.remove(nearest_request)
                nearest_k_vertices.append(temp_dict)

    # assign each customer to a vehicle
    for e in nearest_k_vertices:
        Y[e['vehicle'].id][e['next_stops'][0]] = True
        X[e['vehicle'].id][e['vehicle'].start_stop.location.label][
            e['next_stops'][0]] = True
        X[e['vehicle'].id][e['next_stops'][0]][
            e['vehicle'].start_stop.location.label] = True
        U[e['vehicle'].id][e['vehicle'].start_stop.location.label] = 0
        U[e['vehicle'].id][e['next_stops'][0]] = \
        t[e['vehicle'].start_stop.location.label][e['next_stops'][0]]
        U[e['vehicle'].id][len(G.nodes)] = \
        t[e['vehicle'].start_stop.location.label][e['next_stops'][0]] + \
        d[e['next_stops'][0]] + \
        t[e['next_stops'][0]][e['vehicle'].start_stop.location.label]

        if e['next_stops'][0] in [req.destination.label for req in P]:
            # TODO  : check if the travel time R include the service time of i ? " if so, then you need to add it here"
            R[e['next_stops'][0]] = t[e['next_stops'][0]][
                e['vehicle'].start_stop.location.label]
            W[e['vehicle'].id][e['next_stops'][0]] = q[e['next_stops'][0]]

        if e['next_stops'][0] in [req.origin.label for req in D]:
            # TODO  : check if the travel time R include the service time of i ? " if so, then you need to add it here"
            R[e['next_stops'][0]] = t[e['vehicle'].start_stop.location.label][
                e['next_stops'][0]]
            W[e['vehicle'].id][e['vehicle'].start_stop.location.label] = - q[
                e['next_stops'][0]]
            W[e['vehicle'].id][e['next_stops'][0]] = 0

    # U, R, U_org, R_org = round_all_values(U, R, U_org, R_org)
    # TODO |   in this section we consider that the k nearest vertices will verify
    # TODO |   all constraints if we assign a vehicle for each one
    # TODO |   to do :we should consider the other case where there is some constraints not valid

    # verify if all constraints are verified
    if verify_all_constraints(G.nodes, X, Y, U, W, R, K, V_p, P, T, D, d, q,
                              max_travel_time):
        # if all constraints are valid so we can save the current state as valid one
        # and we need to remove the served customers from V_not_served

        X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org = save_current_solution(
            X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org)
        for e in nearest_k_vertices:
            for req in V_not_served:
                if e['assigned_requests'][0].id == req.id:
                    V_not_served.remove(req)
                    break

        routes = get_routes_dict(X, G, K)
        # plot_routes(routes, G, objective_function(G, K, X), R, P, D, distances)
        print(
            "assign the k nearest vertices from the depot  : Constraints Valid !! Objective_Function==>",
            objective_function(G, K, X))

    else:
        X, Y, U, W, R = back_to_previous_solution(X, Y, U, W, R)
        print(
            "assign the k nearest vertices from the depot  : One or more constraint are not Valid !!")

    # assign the nearest vertex from the last one in a route, for each vehicle (for each route)
    is_possible_to_add = True
    routes = get_routes_dict(X, G, K)
    for e in nearest_k_vertices:
        for k in routes.keys():
            if e['vehicle'].id == k:
                e['route'] = routes[k]
                break

    while len(V_not_served) != 0 and is_possible_to_add:
        is_possible_to_add = False
        for k in routes.keys():
            if len(V_not_served) == 0:
                break

            route_len = len(routes[k])
            if route_len > 2:
                nearest_v, distance, nearest_vertex = nearest_not_served_request(
                    [routes[k][route_len - 2], routes[k][0]], V_not_served, G)
                new_route = add_vertex(G, nearest_vertex,
                                       routes[k][route_len - 2], k, routes[k],
                                       X, Y, U, W, R, d, t, P, D, q)
                if verify_all_constraints(G.nodes, X, Y, U, W, R, K, V_p, P, T,
                                          D, d, q, max_travel_time):
                    is_possible_to_add = True
                    routes[k] = new_route

                    for e in nearest_k_vertices:
                        if e['vehicle'].id == k:
                            e['assigned_requests'].append(nearest_v)
                            e['next_stops'].append(nearest_vertex)
                            e['route'] = routes[k]
                            break

                    X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org = save_current_solution(
                        X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org)
                    # plot_routes(routes, G, objective_function(G, K, X), R, P, D, distances)

                    V_not_served.remove(nearest_v)

                    print("objective function ==> {obj}".format(
                        obj=objective_function(G, K, X)))

                else:
                    X, Y, U, W, R = back_to_previous_solution(X, Y, U, W, R)

    # U, R, U_org, R_org = round_all_values(U, R, U_org, R_org)
    return X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org, nearest_k_vertices


def improve_solution(G, V_not_served, K, X, Y, U, W, R, X_org, Y_org, U_org,
                     W_org, R_org, distances, d, t, V_p, nearest_k_vertices, P,
                     D, q, T, max_travel_time):
    """ Improve the intra-route solution (within each route) """
    # V_p = V_not_served
    routes = get_routes_dict(X, G, K)

    print('routes', routes)
    for i in routes.keys():
        if len(routes[i]) < 3:
            continue

        possible_permutations = []
        route_perm = itertools.permutations(routes[i][1:len(routes[i]) - 1],
                                            len(routes[i]) - 2)
        for tup in route_perm:
            possible_permutations.append([0] + list(tup) + [0])

        pre_route = possible_permutations[0]
        pre_obj_value = objective_function(G, K, X)
        print("before permutation : objective function ==> {obj}".format(
            obj=objective_function(G, K, X)))

        for route in possible_permutations[1:]:
            X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org = \
                save_current_solution(X, Y, U, W, R, X_org, Y_org, U_org,
                                      W_org, R_org)

            X, Y, U, W, R = change_route(G, i, pre_route, route, X, Y, U, W, R,
                                         d, t, P, D, q)
            if not verify_all_constraints(G.nodes, X, Y, U, W, R, K, V_p, P, T,
                                          D, d, q, max_travel_time):
                X, Y, U, W, R = back_to_previous_solution(X, Y, U, W, R)
                continue

            curr_obj_value = objective_function(G, K, X)
            if pre_obj_value >= curr_obj_value:
                X, Y, U, W, R = back_to_previous_solution(X, Y, U, W, R)

            pre_obj_value = objective_function(G, K, X)

        routes = get_routes_dict(X, G, K)
        for e in nearest_k_vertices:
            for k in routes.keys():
                if e['vehicle'].id == k:
                    e['route'] = routes[k]
                    break

        # plot_routes(routes, G, objective_function(G, K, X), R, P, D, distances)

        print("after permutation : objective function ==> {obj}".format(
            obj=objective_function(G, K, X)))

    return X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org, nearest_k_vertices


def update_data(G, non_assigned_requests, vehicles):
    # picked clients
    P = set()

    # delivered clients
    D = set()

    # charge in vertex i , q<0 in delivery  , q>0 in pickup , and 0 for the depot
    # q = [0 for i in G.nodes]
    q = {i: 0 for i in G.nodes}

    depot = "0"
    T = {}

    for req in non_assigned_requests:

        if req.origin.label == depot:
            P.add(req)
            q[req.destination.label] = 1
            # Asma Set departure of train for picked clients
            T[req.destination.label] = req.due_time

        if req.destination.label == depot:
            D.add(req)
            q[req.origin.label] = -1

    return P, D, q, T, non_assigned_requests


def cvrp_pdp_tw_he_obj_cost(G, non_assigned_requests, vehicles):
    max_travel_time = 7200
    distances = get_distances(G)
    # service duration for costumer i
    # it will be considered as 0
    d = [0 for i in range(len(G.nodes))]

    # travel time between vertices
    # let's assume that it depends just on the distance between vertices
    t = get_durations(G)

    P, D, q, T, non_assigned_requests = update_data(G, non_assigned_requests,
                                                    vehicles)

    V_p = set([req.destination.label for req in P]).union(
        set([req.origin.label for req in D]))
    # V_p = non_assigned_requests

    X, Y, U, W, R = variables_declaration(G.nodes, vehicles,
                                          non_assigned_requests)
    X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org, nearest_k_vertices = \
        set_initial_solution(G, non_assigned_requests, vehicles, X, Y, U, W, R,
                             distances, d, t, V_p, P, D, q, T, max_travel_time)
    X, Y, U, W, R, X_org, Y_org, U_org, W_org, R_org, nearest_k_vertices = \
        improve_solution(G, non_assigned_requests, vehicles, X, Y, U, W, R,
                         X_org, Y_org, U_org, W_org, R_org,
                         distances, d, t, V_p, nearest_k_vertices, P, D, q, T,
                         max_travel_time)

    example_name = '15_(8P-7D)_8V'
    with open(example_name + '.csv', mode='w', newline='') as solution_info:
        solution_writer = csv.writer(solution_info, delimiter=',',
                                     quotechar='"', quoting=csv.QUOTE_MINIMAL)
        routes = get_routes_dict(X, G, vehicles)

        head = ['vehicle', 'client', 'Pickup/Delivery',
                'Travel time in this solution', 'Travel time in direct route',
                'Deviation', 'Difference']
        solution_writer.writerow(head)
        for rt in routes.keys():
            for i in routes[rt]:
                if i != 0:
                    travel_time_s = R[i]
                    travel_time_direct_r = (
                        distances[0][i] if i in D else distances[i][0])
                    deviation = (
                                            travel_time_s / travel_time_direct_r - 1) * 100
                    difference = travel_time_s - travel_time_direct_r
                    line = [str(rt), str(i),
                            ('Pickup ' if i in P else 'Delivery '),
                            str(travel_time_s.__round__(3)),
                            str(travel_time_direct_r),
                            str(deviation.__round__(1)) + '%',
                            str(difference.__round__(3))]
                    solution_writer.writerow(line)
    return routes, nearest_k_vertices
