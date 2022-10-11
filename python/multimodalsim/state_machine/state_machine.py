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
    VehicleConnectionCondition, VehicleNoConnectionCondition

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

    def __init__(self, current_state, next_state, triggering_event, condition):
        self.__current_state = current_state
        self.__next_state = next_state
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

    def __init__(self, states=[], initial_state=None, transitions=[]):
        self.__states = states
        self.__current_state = initial_state

        self.__transitions = {}
        for transition in transitions:
            if transition.triggering_event.__name__ in self.__transitions:
                self.__transitions[
                    transition.triggering_event.__name__].append(transition)
            else:
                self.__transitions[
                    transition.triggering_event.__name__] = [transition]

    @property
    def current_state(self):
        return self.__current_state

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


class OptimizationStateMachine(StateMachine):

    def __init__(self):
        idle_state = State("IDLE")
        optimizing_state = State("OPTIMIZING")
        update_environment_state = State("UPDATEENVIRONMENT")

        idle_to_optimizing_transition = Transition(
            idle_state, optimizing_state,
            optimization_event_process.Optimize, TrivialCondition())
        optimizing_to_update_environment_transition = Transition(
            optimizing_state, update_environment_state,
            optimization_event_process.EnvironmentUpdate, TrivialCondition())
        update_environment_to_idle_transition = Transition(
            update_environment_state, idle_state,
            optimization_event_process.EnvironmentIdle, TrivialCondition())

        states = [idle_state, optimizing_state, update_environment_state]
        initial_state = idle_state
        transitions = [idle_to_optimizing_transition,
                       optimizing_to_update_environment_transition,
                       update_environment_to_idle_transition]

        super().__init__(states=states, initial_state=initial_state,
                         transitions=transitions)


class PassengerStateMachine(StateMachine):

    def __init__(self, trip):
        release_state = State("RELEASE")
        assigned_state = State("ASSIGNED")
        ready_state = State("READY")
        on_board_state = State("ONBOARD")
        complete_state = State("COMPLETE")

        release_to_assigned_transition = Transition(
            release_state, assigned_state,
            PassengerAssignment, TrivialCondition())
        assigned_to_ready_environment_transition = Transition(
            assigned_state, ready_state, PassengerReady, TrivialCondition())
        ready_to_on_board_transition = Transition(
            ready_state, on_board_state, PassengerToBoard, TrivialCondition())
        on_board_to_complete_transition = Transition(
            on_board_state, complete_state,
            PassengerAlighting, PassengerNoConnectionCondition(trip))
        on_board_to_release_transition = Transition(
            on_board_state, release_state,
            PassengerAlighting, PassengerConnectionCondition(trip))

        states = [release_state, assigned_state, ready_state, on_board_state,
                  complete_state]
        initial_state = release_state
        transitions = [release_to_assigned_transition,
                       assigned_to_ready_environment_transition,
                       ready_to_on_board_transition,
                       on_board_to_complete_transition,
                       on_board_to_release_transition]

        super().__init__(states=states, initial_state=initial_state,
                         transitions=transitions)


class VehicleStateMachine(StateMachine):

    def __init__(self, route):
        release_state = State("RELEASE")
        boarding_state = State("BOARDING")
        en_route_state = State("ENROUTE")
        alighting_state = State("ALIGHTING")
        complete_state = State("COMPLETE")

        release_to_boarding_transition = Transition(
            release_state, boarding_state,
            VehicleBoarding, VehicleConnectionCondition(route))
        release_to_complete_transition = Transition(
            release_state, complete_state,
            VehicleBoarding, VehicleNoConnectionCondition(route))
        boarding_to_en_route_environment_transition = Transition(
            boarding_state, en_route_state, VehicleDeparture,
            TrivialCondition())
        en_route_to_alighting_transition = Transition(
            en_route_state, alighting_state,
            VehicleArrival, TrivialCondition())
        alighting_to_boarding_transition = Transition(
            alighting_state, boarding_state,
            VehicleBoarding, VehicleConnectionCondition(route))
        alighting_to_complete_transition = Transition(
            alighting_state, complete_state,
            VehicleBoarding, VehicleNoConnectionCondition(route))

        states = [release_state, boarding_state, en_route_state,
                  alighting_state, complete_state]
        initial_state = release_state
        transitions = [release_to_boarding_transition,
                       release_to_complete_transition,
                       boarding_to_en_route_environment_transition,
                       en_route_to_alighting_transition,
                       alighting_to_boarding_transition,
                       alighting_to_complete_transition]

        super().__init__(states=states, initial_state=initial_state,
                         transitions=transitions)
