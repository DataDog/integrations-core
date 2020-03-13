from typing import Any, List, Type

from pyVmomi.vim import ManagedEntity
from pyVmomi.vim.view import ContainerView
from pyVmomi.vmodl import DynamicProperty, ManagedObjectReference

class PropertyCollector:
    class PropertySpec:
        type: Type[ManagedEntity]
        pathSet: List[str]
    class TraversalSpec:
        path: str
        skip: bool
        type: Type[ContainerView]
    class RetrieveOptions:
        maxObjects: int
    class ObjectSpec:
        skip: bool
        selectSet: List[PropertyCollector.TraversalSpec]
        obj: Any
    class FilterSpec:
        propSet: List[PropertyCollector.PropertySpec]
        objectSet: List[PropertyCollector.ObjectSpec]
    def RetrievePropertiesEx(
        self, specSet: List[PropertyCollector.FilterSpec], options: PropertyCollector.RetrieveOptions
    ) -> PropertyCollector.RetrieveResult: ...
    class ObjectContent:
        obj: ManagedObjectReference
        propSet: List[DynamicProperty]
    class RetrieveResult:
        objects: List[PropertyCollector.ObjectContent]
        token: str
    def ContinueRetrievePropertiesEx(self, token: str) -> PropertyCollector.RetrieveResult: ...
