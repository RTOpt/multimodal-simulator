import logging
from itertools import cycle

import multimodalsim.simulator.request as request_module
import multimodalsim.simulator.vehicle as vehicle_module
from multimodalsim.optimization.partition_subset import PartitionSubset, \
    VehiclesLegsPartitionSubset

logger = logging.getLogger(__name__)


class Partition:
    """A Partition object consists essentially of a set of PartitionSubset
    objects that partition all the legs and all the vehicles of the
    simulation."""

    def __init__(self, subsets: list[PartitionSubset]):
        self.__subsets = subsets

    @property
    def subsets(self):
        return self.__subsets

    def add_leg(self, leg: 'request_module.Leg') -> None:
        """Add leg in argument to the Partition if the leg does not already
        belong to one of its PartitionSubset."""
        raise NotImplementedError('add_leg of {} was not implemented'.
                                  format(self.__class__.__name__))

    def add_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        """Add vehicle in argument to the Partition if the vehicle does not
        already belong to one of its PartitionSubset."""
        raise NotImplementedError('add_vehicle of {} was not implemented'.
                                  format(self.__class__.__name__))

    def remove_leg(self, leg: 'request_module.Leg') -> None:
        """Remove the leg in argument from the Partition if the leg belongs to
        one of its PartitionSubset."""
        raise NotImplementedError('remove_leg of {} was not implemented'.
                                  format(self.__class__.__name__))

    def remove_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        """Remove the vehicle in argument from the Partition if the vehicle
        belongs to one of its PartitionSubset."""
        raise NotImplementedError('remove_vehicle of {} was not implemented'.
                                  format(self.__class__.__name__))


class FixedPartition(Partition):
    """A Partition object in which all the PartitionSubset objects that it
    contains are predefined and cannot be modified."""

    def __init__(self, subsets: list[PartitionSubset]):
        super().__init__(subsets)

    def add_leg(self, leg: 'request_module.Leg') -> None:
        """Does nothing since the partition is fixed."""
        pass

    def add_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        """Does nothing since the partition is fixed."""
        pass

    def remove_leg(self, leg: 'request_module.Leg') -> None:
        """Does nothing since the partition is fixed."""
        pass

    def remove_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        """Does nothing since the partition is fixed."""
        pass


class GreedyPartition(Partition):
    """A Partition in which the vehicles and the legs are dynamically
    added to the PartitionSubset objects to generate a mostly uniform
    distribution of vehicles and legs."""

    def __init__(self, nb_subsets: int):
        subset_ids = range(nb_subsets)
        subsets = [VehiclesLegsPartitionSubset(subset_id)
                   for subset_id in subset_ids]
        super().__init__(subsets)

        self.__vehicle_subset_id_iterator = cycle(subset_ids)

    def add_leg(self, leg: 'request_module.Leg') -> None:
        """Add leg to the subset with the least number of legs."""

        non_empty_subsets = [subset for subset in self.subsets
                             if len(subset.vehicle_ids) > 0]
        non_empty_subsets_sorted_by_leg_numbers = \
            sorted(non_empty_subsets, key=lambda x: len(x.leg_ids))

        if len(non_empty_subsets_sorted_by_leg_numbers) > 0:
            current_subset = non_empty_subsets_sorted_by_leg_numbers[0]
        else:
            current_subset = self.subsets[0]

        current_subset.add_leg(leg)

    def add_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        """Add vehicle to the next subset (which should be one of the subsets
        with the least number of vehicles)."""
        subset_id = next(self.__vehicle_subset_id_iterator)
        self.subsets[subset_id].add_vehicle(vehicle)

    def remove_leg(self, leg: 'request_module.Leg') -> None:
        """Remove the leg in argument from the Partition if the leg belongs to
        one of its PartitionSubset."""
        for partition_subset in self.subsets:
            partition_subset.remove_leg(leg)

    def remove_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        """Remove the vehicle in argument from the Partition if the vehicle
        belongs to one of its PartitionSubset."""
        for partition_subset in self.subsets:
            partition_subset.remove_vehicle(vehicle)


class FixedLineGreedyPartition(GreedyPartition):
    """A GreedyPartition in which each leg is dynamically added to a
    feasible PartitionSubset object with the least number of legs."""

    def __init__(self, nb_subsets: int,
                 routes_by_vehicle_id: dict[str | int, vehicle_module.Route]):
        super().__init__(nb_subsets)
        self.__routes_by_vehicle_id = routes_by_vehicle_id

    def add_leg(self, leg: 'request_module.Leg') -> None:
        """Add leg to the subset with the least number of legs in which at
        least one vehicle can serve the leg."""

        feasible_subsets_sorted_by_arrival_time = \
            self.__get_feasible_subsets_sorted_by_arrival_time(leg)

        if len(feasible_subsets_sorted_by_arrival_time) > 0:
            current_subset = feasible_subsets_sorted_by_arrival_time[0]
        else:
            # If no subset has a vehicle that can serve the leg, then add the
            # leg to the first subset.
            logger.warning("No vehicle can serve leg with id: {}".format(
                leg.id))
            current_subset = self.subsets[0]

        current_subset.add_leg(leg)

    def __get_feasible_subsets_sorted_by_arrival_time(self, leg):
        feasible_subsets_by_arrival_time = {}
        for subset in self.subsets:
            min_arrival_time = None
            for vehicle_id in subset.vehicle_ids:
                vehicle_arrival_time = self.__get_vehicle_arrival_time(
                    leg, vehicle_id)
                if vehicle_arrival_time is not None and min_arrival_time is None:
                    min_arrival_time = vehicle_arrival_time
                elif vehicle_arrival_time is not None \
                        and vehicle_arrival_time < min_arrival_time:
                    min_arrival_time = vehicle_arrival_time
            if min_arrival_time is not None:
                feasible_subsets_by_arrival_time[min_arrival_time] = subset

        feasible_subsets_sorted_by_arrival_time = \
            [subset for (arrival_time, subset) in
             sorted(list(feasible_subsets_by_arrival_time.items()),
                    key=lambda x: x[0])]

        return feasible_subsets_sorted_by_arrival_time

    def __get_vehicle_arrival_time(self, leg, vehicle_id):

        origin_feasible = False
        arrival_time = None

        route = self.__routes_by_vehicle_id[vehicle_id]
        current_and_next_stops = [route.current_stop] + route.next_stops \
            if route.current_stop is not None else route.next_stops
        for stop in current_and_next_stops:
            if leg.origin == stop.location \
                    and leg.ready_time <= stop.departure_time:
                origin_feasible = True

            if origin_feasible and leg.destination == stop.location \
                    and leg.due_time >= stop.arrival_time:
                arrival_time = stop.arrival_time
                break

        return arrival_time
