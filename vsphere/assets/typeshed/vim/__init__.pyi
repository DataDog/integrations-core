from datetime import datetime
from typing import Any, List, Type, cast

class ManagedEntity:
    """
    vim.ManagedEntity
    https://www.vmware.com/support/developer/vc-sdk/visdk25pubs/ReferenceGuide/vim.ManagedEntity.html
    """

    _moId: str

ManagedEntityType = Type[ManagedEntity]

class EntityMetricBase:
    """
    vim.ServiceInstance
    https://pubs.vmware.com/vi3/sdk/ReferenceGuide/vim.PerformanceManager.EntityMetricBase.html
    """

    value: Any
    entity: ManagedEntity

class ServiceInstance:
    """
    vim.ServiceInstance
    https://vdc-download.vmware.com/vmwb-repository/dcr-public/b525fb12-61bb-4ede-b9e3-c4a1f8171510/99ba073a-60e9-4933-8690-149860ce8754/doc/vim.ServiceInstance.html
    """

    content: Any
    def CurrentTime(self) -> Any: ...

class PerformanceManager:
    class MetricId:
        """
        vim.PerformanceManager.MetricId
        https://pubs.vmware.com/vi3/sdk/ReferenceGuide/vim.PerformanceManager.MetricId.html
        """

        def __init__(self, counterId: Any, instance: Any): ...
    class CounterInfo:
        """
        vim.PerformanceManager.CounterInfo
        https://vdc-download.vmware.com/vmwb-repository/dcr-public/fe08899f-1eec-4d8d-b3bc-a6664c168c2c/7fdf97a1-4c0d-4be0-9d43-2ceebbc174d9/doc/vim.PerformanceManager.CounterInfo.html
        """

        key: int
        groupInfo: Any
        nameInfo: Any
        rollupType: Any
    class QuerySpec:
        """
        vim.PerformanceManager.QuerySpec
        https://www.vmware.com/support/developer/vc-sdk/visdk41pubs/ApiReference/vim.PerformanceManager.QuerySpec.html
        """

        entity: ManagedEntity
        metricId: List[PerformanceManager.MetricId]
        intervalId: int
        maxSample: int
        startTime: datetime
