from datetime import datetime
from enum import Enum
from typing import Any, List, Type

from pyVmomi.vim.event import EventManager
from pyVmomi.vim.option import OptionManager
from pyVmomi.vim.view import ViewManager
from pyVmomi.vmodl import ManagedObjectReference
from pyVmomi.vmodl.query import PropertyCollector

from . import event as event
from . import fault as fault
from . import view as view

class ManagedEntity:
    """
    vim.ManagedEntity
    https://www.vmware.com/support/developer/vc-sdk/visdk25pubs/ReferenceGuide/vim.ManagedEntity.html
    """

    _moId: str
    obj = None
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

class VirtualMachine(ManagedEntity): ...
class HostSystem(ManagedEntity): ...
class Datacenter(ManagedEntity): ...
class Datastore(ManagedEntity): ...
class ClusterComputeResource(ManagedEntity): ...
class ComputeResource(ManagedEntity): ...
class Folder(ManagedEntity): ...

class VirtualMachinePowerState(Enum):
    poweredOff = 1
    poweredOn = 2
    suspended = 3
