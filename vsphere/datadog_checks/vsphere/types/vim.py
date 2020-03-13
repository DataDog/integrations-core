from datetime import datetime
from typing import Any, List, Type, cast

CounterId = int


class ManagedEntity:
    def __init__(self):
        # type: () -> None
        self._moId = cast(str, None)


ManagedEntityType = Type[ManagedEntity]


class MetricId:
    """ vim.PerformanceManager.MetricId """

    def __init__(self):
        # type: () -> None
        pass


class CounterInfo:
    """
    vim.PerformanceManager.CounterInfo
    """

    def __init__(self):
        # type: () -> None
        self.key = cast(CounterId, None)
        self.groupInfo = cast(Any, None)
        self.nameInfo = cast(Any, None)
        self.rollupType = cast(Any, None)


class QuerySpec:
    """
    vim.PerformanceManager.QuerySpec
    """

    def __init__(self):
        # type: () -> None
        self.entity = cast(ManagedEntity, None)
        self.metricId = cast(List[MetricId], None)
        self.intervalId = cast(int, None)
        self.maxSample = cast(int, None)
        self.startTime = cast(datetime, None)


class ServiceInstance:
    """
    vim.ServiceInstance
    """

    def __init__(self):
        # type: () -> None
        self.content = cast(Any, None)

    def CurrentTime(self):
        # type: () -> Any
        pass
