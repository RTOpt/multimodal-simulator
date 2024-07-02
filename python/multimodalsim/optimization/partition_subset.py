from typing import Optional

import multimodalsim.simulator.request as request_module
import multimodalsim.simulator.vehicle as vehicle_module


class PartitionSubset:
    """A PartitionSubset object is a subset of the leg-vehicle partition.
    It specifies if a leg or a vehicle is an element of the subset. Note that
    all the PartitionSubset objects of a given Partition should be disjoint
    and their union should include all the legs and the vehicles of the
    simulation (i.e., each leg and each vehicle are in one and only one
    PartitionSubset)"""

    def __init__(self, id: str | int):
        self.__id = id

    @property
    def id(self):
        return self.__id

    def is_leg_in(self, leg: 'request_module.Leg') -> bool:
        """Returns True if leg belongs to the PartitionSubset."""
        raise NotImplementedError('is_leg_in of {} was not implemented'.
                                  format(self.__class__.__name__))

    def is_vehicle_in(self, vehicle: 'vehicle_module.Vehicle') -> bool:
        """Returns True if vehicle belongs to the PartitionSubset."""
        raise NotImplementedError('is_vehicle_in of {} was not implemented'.
                                  format(self.__class__.__name__))

    def add_leg(self, leg: 'request_module.Leg') -> None:
        """Add leg in argument to the PartitionSubset if the leg does not
        already belong to it."""
        raise NotImplementedError('add_leg of {} was not implemented'.
                                  format(self.__class__.__name__))

    def add_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        """Add vehicle in argument to the PartitionSubset if the vehicle does
        not already belong to it."""
        raise NotImplementedError('add_vehicle of {} was not implemented'.
                                  format(self.__class__.__name__))

    def remove_leg(self, leg: 'request_module.Leg') -> None:
        """Remove the leg in argument from the PartitionSubset if the leg
        belongs to it."""
        raise NotImplementedError('remove_leg of {} was not implemented'.
                                  format(self.__class__.__name__))

    def remove_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        """Remove the vehicle in argument from the PartitionSubset if the
        vehicle belongs to it."""
        raise NotImplementedError('remove_vehicle of {} was not implemented'.
                                  format(self.__class__.__name__))


class VehiclesLegsPartitionSubset(PartitionSubset):
    """A concrete PartitionSubset where a leg (vehicle) belongs to the
    partition subset if its id belongs to a predefined list of leg (vehicle)
    ids"""
    def __init__(self, id: str | int,
                 vehicle_ids: Optional[list[str | int]] = None,
                 leg_ids: Optional[list[str | int]] = None):
        super().__init__(id)
        self.__vehicle_ids = set(vehicle_ids) if vehicle_ids is not None \
            else set()
        self.__leg_ids = set(leg_ids) if leg_ids is not None else set()

    @property
    def leg_ids(self) -> set[str | int]:
        return self.__leg_ids

    @property
    def vehicle_ids(self) -> set[str | int]:
        return self.__vehicle_ids

    def is_leg_in(self, leg: "request_module.Leg") -> bool:
        return leg.id in self.leg_ids

    def is_vehicle_in(self, vehicle: "vehicle_module.Vehicle") -> bool:
        return vehicle.id in self.vehicle_ids

    def add_leg(self, leg: 'request_module.Leg') -> None:
        self.__leg_ids.add(leg.id)

    def add_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        self.__vehicle_ids.add(vehicle.id)

    def remove_leg(self, leg: 'request_module.Leg') -> None:
        self.__leg_ids.discard(leg.id)

    def remove_vehicle(self, vehicle: 'vehicle_module.Vehicle') -> None:
        self.__vehicle_ids.discard(vehicle.id)