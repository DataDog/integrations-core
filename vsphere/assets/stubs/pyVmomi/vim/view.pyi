from typing import List, Type

from pyVmomi.vim import ManagedEntity

class ContainerView:
    def Destroy(self) -> None: ...

class ViewManager:
    # Note, doc says the type is List[str], but in practice it seems to be List[Type[ManagedEntity]]
    # https://pubs.vmware.com/vi-sdk/visdk250/ReferenceGuide/vim.view.ViewManager.html
    @staticmethod
    def CreateContainerView(
        container: ManagedEntity, type: List[Type[ManagedEntity]], recursive: bool
    ) -> ContainerView: ...
