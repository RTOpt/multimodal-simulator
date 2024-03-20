class EnvironmentStatisticsExtractor:
    def __init__(self) -> None:
        pass

    def extract_environment_statistics(self, env) \
            -> 'EnvironmentStatistics':
        current_time = env.current_time
        nb_vehicles = len(env.vehicles)
        nb_trips = len(env.trips)

        return EnvironmentStatistics(current_time, nb_vehicles, nb_trips)


class EnvironmentStatistics:

    def __init__(self, current_time, nb_vehicles, nb_trips) -> None:
        self.__current_time = current_time
        self.__nb_vehicles = nb_vehicles
        self.__nb_trips = nb_trips

    @property
    def current_time(self) -> int:
        return self.__current_time

    @property
    def nb_vehicles(self) -> int:
        return self.__nb_vehicles

    @property
    def nb_trips(self) -> int:
        return self.__nb_trips
