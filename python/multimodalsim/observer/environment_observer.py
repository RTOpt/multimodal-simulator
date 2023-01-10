from multimodalsim.observer.data_collector import StandardDataCollector, \
    DataContainer
from multimodalsim.observer.visualizer import ConsoleVisualizer
from multimodalsim.statistics.data_analyzer import FixedLineDataAnalyzer


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
        data_container = DataContainer()

        super().__init__(data_collectors=StandardDataCollector(data_container),
                         visualizers=ConsoleVisualizer(
                             data_analyzer=
                             FixedLineDataAnalyzer(data_container)))


