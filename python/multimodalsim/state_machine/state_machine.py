import logging

import multimodalsim.simulator.optimization_event_process \
    as optimization_event_process
from multimodalsim.simulator.passenger_event_process \
    import PassengerAssignment, PassengerReady, PassengerToBoard, \
    PassengerAlighting
from multimodalsim.simulator.vehicle_event_process import VehicleBoarding, \
    VehicleDeparture, VehicleArrival
from multimodalsim.state_machine.condition import TrivialCondition, \
    PassengerNoConnectionCondition, PassengerConnectionCondition, \
    VehicleNextStopCondition, VehicleNoNextStopCondition

logger = logging.getLogger(__name__)


class State:

    def __init__(self, name):
        self.__name = name

    @property
    def name(self):
        return self.__name

    def __str__(self):
        return self.name


class Transition:

    def __init__(self, source_state, target_state, triggering_event,
                 condition):
        self.__current_state = source_state
        self.__next_state = target_state
        self.__triggering_event = triggering_event
        self.__condition = condition

    @property
    def current_state(self):
        return self.__current_state

    @property
    def next_state(self):
        return self.__next_state

    @property
    def triggering_event(self):
        return self.__triggering_event

    @property
    def condition(self):
        return self.__condition


class StateMachine:

    def __init__(self, states=None, initial_state=None, transitions=[]):
        if states is None:
            self.__states = []
        else:
            self.__states = states

        self.__current_state = initial_state

        self.__transitions = {}
        for transition in transitions:
            self.__add_transition_to_transitions(transition)

    @property
    def current_state(self):
        return self.__current_state

    @current_state.setter
    def current_state(self, current_state):
        if self.__current_state is not None:
            raise ValueError("You cannot modify the current state.")
        if isinstance(current_state, str):
            # current_state is the name of the state.
            current_state = self.__get_state(current_state)

        self.__current_state = current_state

    def add_transition(self, source_name, target_name, triggering_event,
                       condition):

        source_state = self.__get_state(source_name)
        target_state = self.__get_state(target_name)
        transition = Transition(source_state, target_state, triggering_event,
                                condition)
        self.__add_transition_to_transitions(transition)

        return transition

    def next_state(self, event):

        logger.debug("EVENT: {}".format(event.__name__))
        logger.debug("current state: {}".format(self.__current_state))
        logger.debug("self.__transitions={}".format(self.__transitions))

        if event.__name__ in self.__transitions:
            transition_possible = False
            for transition in self.__transitions[event.__name__]:
                logger.debug("STATE: {} -> {} | check: {}".format(
                    transition.current_state, transition.next_state,
                    transition.condition.check()))
                if transition.current_state == self.__current_state \
                        and transition.condition.check():
                    self.__current_state = transition.next_state
                    transition_possible = True
                    logger.debug("TRANSITION FOUND!")
                    break

            if not transition_possible:
                raise ValueError(
                    "Event {} is not possible from status {}!".format(
                        event, self.__current_state))

        logger.debug("next state: {}".format(self.__current_state))

        return self.__current_state

    def __add_transition_to_transitions(self, transition):

        if transition.triggering_event.__name__ in self.__transitions:
            self.__transitions[
                transition.triggering_event.__name__].append(transition)
        else:
            self.__transitions[
                transition.triggering_event.__name__] = [transition]

    def __get_state(self, state_name):
        """Return the State with name state_name. Construct it if it does not
        already exist."""
        state = self.__find_state_by_name(state_name)
        if state is None:
            state = State(state_name)
            self.__states.append(state)

        return state

    def __find_state_by_name(self, state_name):
        """Return the State with name state_name if it exists else return
        None."""

        found_state = None
        for state in self.__states:
            if state.name == state_name:
                found_state = state

        return found_state


class OptimizationStateMachine(StateMachine):

    def __init__(self):
        super().__init__()

        self.add_transition("IDLE", "OPTIMIZING",
                            optimization_event_process.Optimize,
                            TrivialCondition())
        self.add_transition("OPTIMIZING", "UPDATEENVIRONMENT",
                            optimization_event_process.EnvironmentUpdate,
                            TrivialCondition())
        self.add_transition("UPDATEENVIRONMENT", "IDLE",
                            optimization_event_process.EnvironmentIdle,
                            TrivialCondition())

        self.current_state = "IDLE"


class PassengerStateMachine(StateMachine):

    def __init__(self, trip):
        super().__init__()

        self.add_transition("RELEASE", "ASSIGNED", PassengerAssignment,
                            TrivialCondition())
        self.add_transition("ASSIGNED", "READY", PassengerReady,
                            TrivialCondition())
        self.add_transition("READY", "ONBOARD", PassengerToBoard,
                            TrivialCondition())
        self.add_transition("ONBOARD", "COMPLETE", PassengerAlighting,
                            PassengerNoConnectionCondition(trip))
        self.add_transition("ONBOARD", "RELEASE", PassengerAlighting,
                            PassengerConnectionCondition(trip))

        self.current_state = "RELEASE"


class VehicleStateMachine(StateMachine):

    def __init__(self, route):
        super().__init__()

        self.add_transition("RELEASE", "BOARDING", VehicleBoarding,
                            VehicleNextStopCondition(route))
        self.add_transition("RELEASE", "COMPLETE", VehicleBoarding,
                            VehicleNoNextStopCondition(route))
        self.add_transition("BOARDING", "ENROUTE", VehicleDeparture,
                            TrivialCondition())
        self.add_transition("ENROUTE", "ALIGHTING", VehicleArrival,
                            TrivialCondition())
        self.add_transition("ALIGHTING", "BOARDING", VehicleBoarding,
                            VehicleNextStopCondition(route))
        self.add_transition("ALIGHTING", "COMPLETE", VehicleBoarding,
                            VehicleNoNextStopCondition(route))

        self.current_state = "RELEASE"

