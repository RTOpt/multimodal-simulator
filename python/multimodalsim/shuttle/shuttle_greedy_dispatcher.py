from multimodalsim.optimization.dispatcher import ShuttleDispatcher
from multimodalsim.shuttle.solution_construction import cvrp_pdp_tw_he_obj_cost


class ShuttleGreedyDispatcher(ShuttleDispatcher):

    def __init__(self, network):
        super().__init__(network)

    def optimize(self, network, non_assigned_requests, vehicles):
        return cvrp_pdp_tw_he_obj_cost(network, non_assigned_requests,
                                       vehicles)
