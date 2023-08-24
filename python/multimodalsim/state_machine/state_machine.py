import logging
from enum import Enum

import multimodalsim.simulator.optimization_event \
    as optimization_event_process
from multimodalsim.simulator.passenger_event \
    import PassengerAssignment, PassengerReady, PassengerToBoard, \
    PassengerAlighting
from multimodalsim.state_machine.status import OptimizationStatus, \
    PassengersStatus, VehicleStatus
from multimodalsim.simulator.vehicle_event import VehicleBoarding, \
    VehicleDeparture, VehicleArrival, VehicleWaiting, VehicleComplete
from multimodalsim.state_machine.condition import TrivialCondition, \
    PassengerNoConnectionCondition, PassengerConnectionCondition

logger = logging.getLogger(__name__)


class State:

    def __init__(self, status):
        self.__status = status

    @property
    def status(self):
        return self.__status

    def __str__(self):
        return str(self.status)


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

    def __init__(self, states=None, initial_state=None, transitions=[],
                 owner=None):

        if states is None:
            self.__states = []
        else:
            self.__states = states

        self.__current_state = initial_state

        self.__transitions = {}
        for transition in transitions:
            self.__add_transition_to_transitions(transition)

        self.__owner = owner

    @property
    def owner(self):
        return self.__owner

    @property
    def current_state(self):
        return self.__current_state

    @property
    def transitions(self):
        return self.__transitions

    @current_state.setter
    def current_state(self, current_state):
        if self.__current_state is not None:
            raise ValueError("You cannot modify the current state.")
        if isinstance(current_state, Enum):
            # Here, current_state is the status of the state.
            current_state = self.__get_state(current_state)

        self.__current_state = current_state

    def add_transition(self, source_status, target_status, triggering_event,
                       condition=None):
        if condition is None:
            condition = TrivialCondition()

        source_state = self.__get_state(source_status)
        target_state = self.__get_state(target_status)
        transition = Transition(source_state, target_state, triggering_event,
                                condition)
        self.__add_transition_to_transitions(transition)

        return transition

    def next_state(self, event, env):

        transition_possible = False
        if event.__name__ in self.__transitions:
            for transition in self.__transitions[event.__name__]:
                # logger.debug("STATE: {} -> {} | check: {}".format(str(
                # transition.current_state), str(transition.next_state),
                # transition.condition.check()))
                if transition.current_state == self.__current_state \
                        and transition.condition.check(env):
                    self.__current_state = transition.next_state
                    transition_possible = True
                    # logger.debug("TRANSITION FOUND!")
                    break

        if not transition_possible:
            raise ValueError(
                "Event {} is not possible from status {}!".format(
                    event, self.__current_state))

        return self.__current_state

    def __add_transition_to_transitions(self, transition):

        if transition.triggering_event.__name__ in self.__transitions:
            self.__transitions[
                transition.triggering_event.__name__].append(transition)
        else:
            self.__transitions[
                transition.triggering_event.__name__] = [transition]

    def __get_state(self, state_status):
        """Return the State with status state_status. Construct it if it does not
        already exist."""
        state = self.__find_state_by_status(state_status)
        if state is None:
            state = State(state_status)
            self.__states.append(state)

        return state

    def __find_state_by_status(self, state_status):
        """Return the State with status state_status if it exists else return
        None."""

        found_state = None
        for state in self.__states:
            if state.status == state_status:
                found_state = state

        return found_state


class OptimizationStateMachine(StateMachine):

    def __init__(self, optimization):
        super().__init__(owner=optimization)
        self.add_transition(OptimizationStatus.IDLE,
                            OptimizationStatus.OPTIMIZING,
                            optimization_event_process.Optimize)
        self.add_transition(OptimizationStatus.OPTIMIZING,
                            OptimizationStatus.UPDATEENVIRONMENT,
                            optimization_event_process.EnvironmentUpdate)
        self.add_transition(OptimizationStatus.UPDATEENVIRONMENT,
                            OptimizationStatus.IDLE,
                            optimization_event_process.EnvironmentIdle)

        self.current_state = OptimizationStatus.IDLE


class PassengerStateMachine(StateMachine):

    def __init__(self, trip):
        super().__init__(owner=trip)

        self.add_transition(PassengersStatus.RELEASE,
                            PassengersStatus.ASSIGNED, PassengerAssignment)
        self.add_transition(PassengersStatus.ASSIGNED,
                            PassengersStatus.ASSIGNED, PassengerAssignment)
        self.add_transition(PassengersStatus.READY,
                            PassengersStatus.ASSIGNED, PassengerAssignment)
        self.add_transition(PassengersStatus.ASSIGNED, PassengersStatus.READY,
                            PassengerReady)
        self.add_transition(PassengersStatus.READY, PassengersStatus.ONBOARD,
                            PassengerToBoard)
        self.add_transition(PassengersStatus.ONBOARD,
                            PassengersStatus.COMPLETE, PassengerAlighting,
                            PassengerNoConnectionCondition(trip))
        self.add_transition(PassengersStatus.ONBOARD, PassengersStatus.RELEASE,
                            PassengerAlighting,
                            PassengerConnectionCondition(trip))

        self.current_state = PassengersStatus.RELEASE


class VehicleStateMachine(StateMachine):

    def __init__(self, vehicle):
        super().__init__(owner=vehicle)

        self.add_transition(VehicleStatus.RELEASE, VehicleStatus.IDLE,
                            VehicleWaiting)
        self.add_transition(VehicleStatus.IDLE, VehicleStatus.IDLE,
                            VehicleWaiting)
        self.add_transition(VehicleStatus.IDLE, VehicleStatus.BOARDING,
                            VehicleBoarding)
        self.add_transition(VehicleStatus.IDLE, VehicleStatus.ENROUTE,
                            VehicleDeparture)
        self.add_transition(VehicleStatus.BOARDING, VehicleStatus.IDLE,
                            VehicleWaiting)
        self.add_transition(VehicleStatus.ENROUTE, VehicleStatus.ALIGHTING,
                            VehicleArrival)
        self.add_transition(VehicleStatus.ALIGHTING, VehicleStatus.IDLE,
                            VehicleWaiting)
        self.add_transition(VehicleStatus.IDLE, VehicleStatus.COMPLETE,
                            VehicleComplete)

        self.current_state = VehicleStatus.RELEASE
