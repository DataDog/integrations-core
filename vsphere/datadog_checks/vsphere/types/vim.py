from datetime import datetime
from typing import Any, List, Type, cast

CounterId = int


class ManagedEntity:
    """
    vim.ManagedEntity
    https://www.vmware.com/support/developer/vc-sdk/visdk25pubs/ReferenceGuide/vim.ManagedEntity.html
    """

    def __init__(self):
        # type: () -> None
        self._moId = cast(str, None)


ManagedEntityType = Type[ManagedEntity]


class MetricId:
    """
    vim.PerformanceManager.MetricId
    https://pubs.vmware.com/vi3/sdk/ReferenceGuide/vim.PerformanceManager.MetricId.html
    """

    def __init__(self):
        # type: () -> None
        pass


class CounterInfo:
    """
    vim.PerformanceManager.CounterInfo
    https://vdc-download.vmware.com/vmwb-repository/dcr-public/fe08899f-1eec-4d8d-b3bc-a6664c168c2c/7fdf97a1-4c0d-4be0-9d43-2ceebbc174d9/doc/vim.PerformanceManager.CounterInfo.html
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
    https://www.vmware.com/support/developer/vc-sdk/visdk41pubs/ApiReference/vim.PerformanceManager.QuerySpec.html
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
    https://vdc-download.vmware.com/vmwb-repository/dcr-public/b525fb12-61bb-4ede-b9e3-c4a1f8171510/99ba073a-60e9-4933-8690-149860ce8754/doc/vim.ServiceInstance.html
    """

    def __init__(self):
        # type: () -> None
        self.content = cast(Any, None)

    def CurrentTime(self):
        # type: () -> Any
        pass


class EntityMetricBase:
    """
    vim.ServiceInstance
    https://pubs.vmware.com/vi3/sdk/ReferenceGuide/vim.PerformanceManager.EntityMetricBase.html
    """

    def __init__(self):
        # type: () -> None
        self.value = cast(Any, None)
        self.entity = cast(ManagedEntity, None)


class Event:
    """
    vim.event.Event
    https://vdc-repo.vmware.com/vmwb-repository/dcr-public/fe08899f-1eec-4d8d-b3bc-a6664c168c2c/7fdf97a1-4c0d-4be0-9d43-2ceebbc174d9/doc/vim.event.Event.html
    """

    def __init__(self):
        # type: () -> None
        pass
