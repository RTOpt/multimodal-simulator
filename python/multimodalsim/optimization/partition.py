class Partition:
    def __init__(self, subsets: list['PartitionSubset']):
        self.__subsets = subsets

    @property
    def subsets(self):
        return self.__subsets


class PartitionSubset:
    def __init__(self, id, leg_ids: list[str | int], vehicle_ids: list[str | int]):
        self.__id = id
        self.__leg_ids = set(leg_ids)
        self.__vehicle_ids = set(vehicle_ids)

    @property
    def id(self):
        return self.__id

    @property
    def leg_ids(self):
        return self.__leg_ids

    @property
    def vehicle_ids(self):
        return self.__vehicle_ids
