import copy


class State(object):

    def __init__(self, env):
        env_deep_copy = copy.deepcopy(env)

        self.current_time = env_deep_copy.current_time
        self.trips = env_deep_copy.trips
        self.assigned_trips = env_deep_copy.assigned_trips
        self.non_assigned_trips = env_deep_copy.non_assigned_trips
        self.vehicles = env_deep_copy.vehicles
        self.assigned_vehicles = env_deep_copy.assigned_vehicles
        self.non_assigned_vehicles = env_deep_copy.non_assigned_vehicles
