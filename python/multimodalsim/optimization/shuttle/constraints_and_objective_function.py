import logging

logger = logging.getLogger(__name__)


def variables_declaration(V, K, V_p):
    # K : set of vehicles
    # V : set of vertices
    # V_p : set of customers
    # binary represent if the arc i to j is traversed by the vehicle k
    # initialized with False
    # X = [[[False for j in range(len(V))] for i in range(len(V))] for k in range(len(K))]
    X = {k.id: {i: {j: False for j in V} for i in V} for k in K}

    # binary represent if the vehicle k serve client at vertex i
    # initialized with False
    # Y = [[False for i in range(len(V))] for k in range(len(K))]
    Y = {k.id: {i: False for i in V} for k in K}

    # the moment the vehicle k arrives at vertex i
    # U[k][0] the arrival at the station for pickup
    # and U[k][n+1] arrival at the station for delivery
    # initialized with -1
    # U = [[-1 for i in range(len(V) + 1)] for k in range(len(K))]
    U = {k.id: dict({i: -1 for i in V}, **{'sink': -1}) for k in K}

    # the load of vehicle k in vertex i
    # initialized with 0
    # W = [[0 for i in range(len(V))] for k in range(len(K))]
    W = {k.id: {i: 0 for i in V} for k in K}

    # travel time for customers at vertex i
    # initialized with 0
    R = {i: 0 for i in V}

    # set of not served customers
    # V_not_served = set(V_p)
    # V_not_served = V_p

    return X, Y, U, W, R

def verify_const_2(V, X, Y, K, V_p):

    verified = True

    for f_k in K:
        for f_i in V_p:
            sum_x = 0
            for f_j in V:
                if f_i != f_j:
                    sum_x += (1 if X[f_k.id][f_i][f_j] else 0)

            y_i_k = 1 if Y[f_k.id][f_i] else 0
            if y_i_k != sum_x:
                verified = False
                break

        if not verified:
            break

    return verified


def verify_const_3(Y, K, V):

    verified = True
    for f_i in V:
        sum_y = 0
        for f_k in K:
            sum_y += (1 if Y[f_k.id][f_i] else 0)
        if sum_y > 1:
            verified = False
            break

    return verified

def verify_const_4(X, K, V):
    hub_id = '0'

    verified = True
    for f_k in K:
        sum_x = 0
        for f_j in V:
            sum_x += (1 if X[f_k.id][hub_id][f_j] else 0)
        if sum_x > 1:
            verified = False
            break

    return verified

def verify_const_5(V, X, K, V_p):

    verified = True
    for f_i in V_p:
        for f_k in K:
            sum_x_1 = 0
            sum_x_2 = 0
            for f_j in V:
                if f_i != f_j:
                    sum_x_1 += (1 if X[f_k.id][f_i][f_j] else 0)
                    sum_x_2 += (1 if X[f_k.id][f_i][f_j] else 0)
            if sum_x_1 != sum_x_2:
                verified = False
                break

        if not verified:
            break

    return verified


def verify_const_6():

    verified = True
    # TODO define this constraint
    # TODO what is T in this constraint
    return verified


def verify_const_7(V, Y, R, U, K, P, T, d):

    verified = True
    for f_k in K:
        for f_i in [req.destination.label for req in P]:
            f_sum = U[f_k.id]['sink'] - (U[f_k.id][f_i] + d[f_i]) - (T[f_i] - d[f_i]) * (1 - (1 if Y[f_k.id][f_i] else 0))
            if R[f_i] < f_sum.__round__(2):
                verified = False
                break
        if not verified:
            break

    return verified

def verify_const_8(R, U, K, D, d):

    verified = True
    for f_k in K:
        for f_i in [req.origin.label for req in D]:
            if R[f_i] < U[f_k.id][f_i] - d[f_i] - U[f_k.id][f_i]:
                verified = False
                break
        if not verified:
            break

    return verified

def verify_const_9():

    verified = True
    # TODO define this constraint
    # TODO what is T in this constraint
    return verified

def verify_const_10_a(R, P, max_travel_time):

    verified = True
    # TODO : This Constraint is changed ( we took just the first part )
    for f_i in [req.destination.label for req in P]:
        if R[f_i] > max_travel_time:
            verified = False
            break

    return verified

def verify_const_10_b(R, D, max_travel_time):

    verified = True
    # TODO : This Constraint is changed ( we took just the first part )
    for f_i in [req.origin.label for req in D]:
        if R[f_i] > max_travel_time:
            verified = False
            break

    return verified

def verify_const_11(Y, U, K, D):

    verified = True
    for f_k in K:
        for req in D:
            f_i = req.origin.label
            ready_time_f_i = req.ready_time
            due_time_f_i = req.due_time
            if U[f_k.id][f_i] != -1 and (ready_time_f_i * Y[f_k.id][f_i] > U[f_k.id][f_i] or U[f_k.id][f_i] > due_time_f_i * Y[f_k.id][f_i]):
                verified = False
                break
        if not verified:
            break

    return verified

def verify_const_12(Y, K, D, P, q):

    verified = True
    for f_k in K:
        sum_y_q = 0
        for f_i in [req.destination.label for req in P]:
            sum_y_q += Y[f_k.id][f_i] * q[f_i]
        if sum_y_q > f_k.capacity:
            verified = False
            break

        sum_y_q = 0
        for f_i in [req.origin.label for req in D]:
            sum_y_q += Y[f_k.id][f_i] * (-1 * q[f_i])
        if sum_y_q > f_k.capacity:
            verified = False
            break

    return verified

def verify_const_13():

    verified = True
    # TODO    define this constraint
    # TODO    This constraint it's not clear
    # TODO    what means i<j (vertex < vertex) and l<k (vehicle < vehicle)
    return verified

def verify_const_14():

    verified = True
    # TODO    define this constraint
    # TODO    This constraint it's not clear
    # TODO    what is i ??
    return verified

def verify_const_15(V, W, K):

    verified = True
    for f_k in K:
        for f_i in V:
            if W[f_k.id][f_i] < 0 or W[f_k.id][f_i] > f_k.capacity:
                verified = False
                break
        if not verified:
            break

    return verified


def verify_all_constraints(V, X, Y, U, W, R, K, V_p, P, T, D, d, q, max_travel_time):

    return verify_const_2(V, X, Y, K, V_p) and \
           verify_const_3(Y, K, V_p) and \
           verify_const_4(X, K, V_p) and \
           verify_const_5(V, X, K, V_p) and \
           verify_const_6() and \
           verify_const_7(V, Y, R, U, K, P, T, d) and \
           verify_const_8(R, U, K, D, d) and \
           verify_const_9() and \
           verify_const_10_a(R, P, max_travel_time) and \
           verify_const_10_b(R, D, max_travel_time) and \
           verify_const_11(Y, U, K, D) and \
           verify_const_12(Y, K, D, P, q) and \
           verify_const_13() and \
           verify_const_14() and \
           verify_const_15(V, W, K)



def objective_function(G, K , X):
    """ This objective function is used to maximise the (-1)*cost """

    value = 0
    for f_k in K:
        for node1, node2, data in G.edges(data=True):
            value -= data['cost'] * (1 if X[f_k.id][node1][node2] else 0)

    return value.__round__(3)

def total_deviation(G, f_routes, R, D):
    """ This objective function is used to minimise the deviation """

    value = 0
    for f_rt in f_routes.keys():
        for f_i in f_routes[f_rt]:
            if f_i != 0:
                travel_time_solution = R[f_i]
                travel_time_direct_route = (G[0][f_i]['cost'] if f_i in D else G[f_i][0]['cost'])
                f_deviation = (travel_time_solution/travel_time_direct_route - 1) * 100
                value -= f_deviation

    return value.__round__(1)
