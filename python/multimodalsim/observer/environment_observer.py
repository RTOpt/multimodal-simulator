from multimodalsim.config.config import DataContainerConfig
from multimodalsim.observer.data_collector import StandardDataCollector
from multimodalsim.observer.visualizer import ConsoleVisualizer


class EnvironmentObserver:

    def __init__(self, data_collectors=None, visualizers=None):

        if data_collectors is not None and type(data_collectors) is not list:
            self.__data_collectors = [data_collectors]
        elif data_collectors is not None:
            self.__data_collectors = data_collectors
        else:
            self.__data_collectors = []

        if visualizers is not None and type(visualizers) is not list:
            self.__visualizers = [visualizers]
        elif visualizers is not None:
            self.__visualizers = visualizers
        else:
            self.__visualizers = []

    @property
    def data_collectors(self):
        return self.__data_collectors

    @property
    def visualizers(self):
        return self.__visualizers


class StandardEnvironmentObserver(EnvironmentObserver):

    def __init__(self):

        data_collector = self.__get_standard_data_collector()

        super().__init__(data_collectors=data_collector,
                         visualizers=ConsoleVisualizer())

    def __get_standard_data_collector(self):

        config = DataContainerConfig()

        data_collector = StandardDataCollector(vehicles_columns=config.
                                               get_vehicles_columns(),
                                               trips_columns=config.
                                               get_trips_columns(),
                                               events_columns=config.
                                               get_events_columns())

        return data_collector

