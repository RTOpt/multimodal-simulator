class State(object):

    def __init__(self, env):

        # Deep copy of env (faire attention aux objets qui sont les mêmes)
        # Créer les objets vides et réassigner tout.

        # Ajouter des méthodes deep_copy

        self.non_assigned_trips = None
        self.current_time = 0
        self.trips = []
        self.assigned_trips = []
        self.non_assigned_trips = []
        self.vehicles = []
        self.assigned_vehicles = []
        self.non_assigned_vehicles = []