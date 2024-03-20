import logging
from enum import Enum
from typing import Type, Optional, Any

import multimodalsim.simulator.optimization_event \
    as optimization_event_process
import multimodalsim.optimization.optimization as optimization_module
from multimodalsim.simulator.event import Event
from multimodalsim.simulator.passenger_event \
    import PassengerAssignment, PassengerReady, PassengerToBoard, \
    PassengerAlighting
from multimodalsim.state_machine.status import OptimizationStatus, \
    PassengerStatus, VehicleStatus, Status
from multimodalsim.simulator.vehicle_event import VehicleBoarding, \
    VehicleDeparture, VehicleArrival, VehicleWaiting, VehicleComplete
from multimodalsim.state_machine.condition import TrivialCondition, \
    PassengerNoConnectionCondition, PassengerConnectionCondition, Condition
import multimodalsim.simulator.environment as environment
import multimodalsim.simulator.vehicle as vehicle_module
import multimodalsim.simulator.request as request

logger = logging.getLogger(__name__)


class State:

    def __init__(self, status: Status) -> None:
        self.__status = status

    @property
    def status(self) -> Status:
        return self.__status

    def __str__(self):
        return str(self.status)


class Transition:

    def __init__(self, source_state: State, target_state: State,
                 triggering_event: Type[Event], condition: Condition):
        self.__current_state = source_state
        self.__next_state = target_state
        self.__triggering_event = triggering_event
        self.__condition = condition

    @property
    def current_state(self) -> State:
        return self.__current_state

    @property
    def next_state(self) -> State:
        return self.__next_state

    @property
    def triggering_event(self) -> Type[Event]:
        return self.__triggering_event

    @property
    def condition(self) -> Condition:
        return self.__condition


class StateMachine:

    def __init__(self, states: Optional[list[State]] = None,
                 initial_state: Optional[State] = None,
                 transitions: Optional[list[Transition]] = None,
                 owner: Optional[Any] = None) -> None:

        if transitions is None:
            transitions = []

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
    def owner(self) -> Optional[Any]:
        return self.__owner

    @property
    def current_state(self) -> Optional[State]:
        return self.__current_state

    @property
    def transitions(self) -> Optional[dict[Transition]]:
        return self.__transitions

    @current_state.setter
    def current_state(self, current_state: State) -> None:
        if self.__current_state is not None:
            raise ValueError("You cannot modify the current state.")
        if isinstance(current_state, Enum):
            # Here, current_state is the status of the state.
            current_state = self.__get_state(current_state)

        self.__current_state = current_state

    def add_transition(self, source_status: Enum, target_status: Enum,
                       triggering_event: Type[Event],
                       condition: Optional[Condition] = None) -> Transition:
        if condition is None:
            condition = TrivialCondition()

        source_state = self.__get_state(source_status)
        target_state = self.__get_state(target_status)
        transition = Transition(source_state, target_state, triggering_event,
                                condition)
        self.__add_transition_to_transitions(transition)

        return transition

    def next_state(self, event: Type[Event],
                   env: 'environment.Environment') -> State:

        transition_possible = False
        if event.__name__ in self.__transitions:
            for transition in self.__transitions[event.__name__]:
                if transition.current_state == self.__current_state \
                        and transition.condition.check(env):
                    self.__current_state = transition.next_state
                    transition_possible = True
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
        """Return the State with status state_status. Construct it if it does
        not already exist."""
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

    def __init__(self,
                 optimization: 'optimization_module.Optimization') -> None:
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

    def __init__(self, trip: 'request.Trip') -> None:
        super().__init__(owner=trip)

        self.add_transition(PassengerStatus.RELEASE,
                            PassengerStatus.ASSIGNED, PassengerAssignment)
        self.add_transition(PassengerStatus.ASSIGNED,
                            PassengerStatus.ASSIGNED, PassengerAssignment)
        self.add_transition(PassengerStatus.READY,
                            PassengerStatus.ASSIGNED, PassengerAssignment)
        self.add_transition(PassengerStatus.ASSIGNED, PassengerStatus.READY,
                            PassengerReady)
        self.add_transition(PassengerStatus.READY, PassengerStatus.READY,
                            PassengerReady)
        self.add_transition(PassengerStatus.READY, PassengerStatus.ONBOARD,
                            PassengerToBoard)
        self.add_transition(PassengerStatus.ONBOARD,
                            PassengerStatus.COMPLETE, PassengerAlighting,
                            PassengerNoConnectionCondition(trip))
        self.add_transition(PassengerStatus.ONBOARD, PassengerStatus.RELEASE,
                            PassengerAlighting,
                            PassengerConnectionCondition(trip))

        self.current_state = PassengerStatus.RELEASE


class VehicleStateMachine(StateMachine):

    def __init__(self, vehicle: 'vehicle_module.Vehicle') -> None:
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
        self.add_transition(VehicleStatus.COMPLETE, VehicleStatus.COMPLETE,
                            VehicleComplete)

        self.current_state = VehicleStatus.RELEASE
