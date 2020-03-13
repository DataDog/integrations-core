from datetime import datetime
from typing import Any, List, cast


class ManagedEntity:
    def __init__(self):
        # type: () -> None
        self._moId = cast(str, None)


class ManagedEntityType:
    def __init__(self):
        # type: () -> None
        pass


class MetricId:
    """ vim.PerformanceManager.MetricId """

    def __init__(self):
        # type: () -> None
        pass


class Counter:
    def __init__(self):
        # type: () -> None
        self.groupInfo = cast(Any, None)
        self.nameInfo = cast(Any, None)
        self.rollupType = cast(Any, None)


class QuerySpec:
    """ vim.PerformanceManager.QuerySpec """

    def __init__(self):
        # type: () -> None
        self.entity = cast(ManagedEntity, None)
        self.metricId = cast(List[MetricId], None)
        self.intervalId = cast(int, None)
        self.maxSample = cast(int, None)
        self.startTime = cast(datetime, None)
