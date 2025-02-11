from typing import Optional

from multimodalsim.observer.data_collector import StandardDataCollector, \
    DataCollector, StandardDataContainer
from multimodalsim.observer.visualizer import ConsoleVisualizer, Visualizer
from multimodalsim.statistics.data_analyzer import FixedLineDataAnalyzer


class EnvironmentObserver:

    def __init__(
            self, data_collectors: Optional[
                DataCollector | list[DataCollector]] = None,
            visualizers: Optional[
                Visualizer | list[Visualizer]] = None
            ) -> None:

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
    def data_collectors(self) -> list[DataCollector]:
        return self.__data_collectors

    @property
    def visualizers(self) -> list[Visualizer]:
        return self.__visualizers


class StandardEnvironmentObserver(EnvironmentObserver):

    def __init__(self) -> None:
        data_container = StandardDataContainer()

        super().__init__(data_collectors=StandardDataCollector(data_container),
                         visualizers=ConsoleVisualizer(
                             data_analyzer=
                             FixedLineDataAnalyzer(data_container)))
