from typing import Any, List, Type  # noqa: F401

from pyVmomi.vim import ManagedEntity  # noqa: F401

class OptionManager:
    def QueryOptions(self, name: str) -> List[OptionValue]: ...

class OptionValue:
    """
    Data Object - OptionValue(vim.option.OptionValue)
    https://vdc-download.vmware.com/vmwb-repository/dcr-public/3325c370-b58c-4799-99ff-58ae3baac1bd/45789cc5-aba1-48bc-a320-5e35142b50af/doc/vim.option.OptionValue.html
    """

    value: Any
