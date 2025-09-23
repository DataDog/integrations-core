from datetime import datetime
from enum import Enum
from typing import Any, List

from . import event  # noqa: F401
from . import fault  # noqa: F401
from . import view  # noqa: F401
from ..vmodl.query import PropertyCollector
from .event import EventManager
from .option import OptionManager
from .view import ViewManager

class ManagedObject: ...

class ManagedEntity(ManagedObject):
    """
    vim.ManagedEntity
    https://www.vmware.com/support/developer/vc-sdk/visdk25pubs/ReferenceGuide/vim.ManagedEntity.html
    """

    _moId: str
    obj: None
    name: str

class ServiceInstanceContent:
    """
    vim.ServiceInstanceContent
    https://vdc-download.vmware.com/vmwb-repository/dcr-public/3325c370-b58c-4799-99ff-58ae3baac1bd/45789cc5-aba1-48bc-a320-5e35142b50af/doc/vim.ServiceInstanceContent.html
    """

    setting: OptionManager
    propertyCollector: PropertyCollector
    rootFolder: Folder
    viewManager: ViewManager
    perfManager: PerformanceManager
    eventManager: EventManager
    about: AboutInfo
    customFieldsManager: CustomFieldsManager

class ServiceInstance:
    """
    vim.ServiceInstance
    https://vdc-download.vmware.com/vmwb-repository/dcr-public/b525fb12-61bb-4ede-b9e3-c4a1f8171510/99ba073a-60e9-4933-8690-149860ce8754/doc/vim.ServiceInstance.html
    """

    content: ServiceInstanceContent
    def CurrentTime(self) -> Any: ...

class PerformanceManager:
    class MetricId:
        """
        vim.PerformanceManager.MetricId
        https://pubs.vmware.com/vi3/sdk/ReferenceGuide/vim.PerformanceManager.MetricId.html
        """

        def __init__(self, counterId: Any, instance: Any): ...
    class PerfCounterInfo:
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
    def QueryPerfCounterByLevel(self, collection_level: int) -> List[PerformanceManager.PerfCounterInfo]: ...
    class EntityMetricBase:
        """
        vim.ServiceInstance
        https://pubs.vmware.com/vi3/sdk/ReferenceGuide/vim.PerformanceManager.EntityMetricBase.html
        """

        value: Any
        entity: ManagedEntity
    def QueryPerf(self, querySpec: List[PerformanceManager.QuerySpec]) -> List[PerformanceManager.EntityMetricBase]: ...


class AboutInfo:
    apiType: str
    apiVersion: str
    version: str
    build: str
    fullName: str

class CustomFieldsManager:
    field: List[FieldDef]

    class FieldDef:
        key: int
        name: str

class VirtualMachine(ManagedEntity): ...
class HostSystem(ManagedEntity): ...
class Datacenter(ManagedEntity): ...
class Datastore(ManagedEntity): ...
class ClusterComputeResource(ManagedEntity): ...
class ComputeResource(ManagedEntity): ...
class Folder(ManagedEntity): ...
class StoragePod(ManagedEntity): ...

class VirtualMachinePowerState(Enum):
    poweredOff: int
    poweredOn: int
    suspended: int

