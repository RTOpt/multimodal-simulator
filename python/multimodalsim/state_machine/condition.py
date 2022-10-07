class Condition:

    def __init__(self, name):
        self.__name = name

    @property
    def name(self):
        return self.__name

    def check(self):
        raise NotImplementedError('Condition.check not implemented')


class TrivialCondition(Condition):

    def __init__(self):
        super().__init__("Trivial")

    def check(self):
        return True


class PassengerNoConnectionCondition(Condition):

    def __init__(self, trip):
        super().__init__("PassengerConnection")
        self.__trip = trip

    def check(self):
        condition_satisfied = False
        if self.__trip.next_legs is None or len(self.__trip.next_legs) == 0:
            condition_satisfied = True

        return condition_satisfied


class PassengerConnectionCondition(Condition):

    def __init__(self, trip):
        super().__init__("PassengerNoConnection")
        self.__trip = trip

    def check(self):
        condition_satisfied = False
        if self.__trip.next_legs is not None and len(self.__trip.next_legs) > 0:
            condition_satisfied = True

        return condition_satisfied


class VehicleConnectionCondition(Condition):

    def __init__(self, route):
        super().__init__("VehicleConnection")
        self.__route = route

    def check(self):
        condition_satisfied = False
        if len(self.__route.next_stops) > 0:
            condition_satisfied = True

        return condition_satisfied


class VehicleNoConnectionCondition(Condition):

    def __init__(self, route):
        super().__init__("VehicleNoConnection")
        self.__route = route

    def check(self):
        condition_satisfied = False
        if len(self.__route.next_stops) == 0:
            condition_satisfied = True

        return condition_satisfied