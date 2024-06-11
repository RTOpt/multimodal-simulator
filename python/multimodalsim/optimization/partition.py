import multimodalsim.simulator.request as request_module
import multimodalsim.simulator.vehicle as vehicle_module


class Partition:
    """A Partition object consists essentially of a set of PartitionSubset
    objects that partition all the legs and all the vehicles of the
    simulation."""
    def __init__(self, subsets: list['PartitionSubset']):
        self.__subsets = subsets

    @property
    def subsets(self):
        return self.__subsets


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


class VehiclesLegsPartitionSubset(PartitionSubset):
    """A concrete PartitionSubset object where a leg (vehicle) belongs to the
    partition subset if its id belongs to a predefined list of leg (vehicle)
    ids"""
    def __init__(self, id: str | int, vehicle_ids: list[str | int],
                 leg_ids: list[str | int]):
        super().__init__(id)
        self.__vehicle_ids = set(vehicle_ids)
        self.__leg_ids = set(leg_ids)

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
