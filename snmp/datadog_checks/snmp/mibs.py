# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import threading
from typing import Dict, Tuple, Optional

from .pysnmp_types import (
    DirMibSource,
    MibBuilder,
    MibInstrumController,
    MibViewController,
    MsgAndPduDispatcher,
    SnmpEngine,
)


BuilderInfo = Tuple[MibBuilder, MibInstrumController, MibViewController]


def _create_mib_builder(mibs_path=None):
    # type: (str) -> BuilderInfo
    mib_builder = MibBuilder()

    if mibs_path is not None:
        mib_builder.addMibSources(DirMibSource(mibs_path))

    mib_instrum = MibInstrumController(mib_builder)
    mib_view = MibViewController(mib_builder)

    return mib_builder, mib_instrum, mib_view


class MIBLoader:
    """
    A helper for loading and caching MIB information using PySNMP.

    To save up memory, PySNMP MIB-related objects are cached by MIB path.

    If this behavior is not desired, you should use separate loader instances.
    """

    def __init__(self):
        # type: () -> None
        self._builders = {}  # type: Dict[Optional[str], BuilderInfo]
        self._cache_lock = threading.Lock()

    def _get_or_create_builder_info(self, mibs_path=None):
        # type: (str) -> BuilderInfo
        with self._cache_lock:  # Prevent concurrent builder cache access and updates.
            if mibs_path not in self._builders:
                self._builders[mibs_path] = _create_mib_builder(mibs_path)
            return self._builders[mibs_path]

    def get_mib_view_controller(self, mibs_path=None):
        # type: (str) -> MibViewController
        """
        Create a PySNMP MibViewController instance, for use in MIB resolution.
        """
        _, _, mib_view_controller = self._get_or_create_builder_info(mibs_path)
        return mib_view_controller

    def create_snmp_engine(self, mibs_path=None):
        # type: (str) -> SnmpEngine
        """
        Create a command generator to perform SNMP queries.

        If `mibs_path` is not None, load the mibs present in the custom MIBs folder. (MIBs must be in PySNMP format.)
        """
        _, instrum_controller, _ = self._get_or_create_builder_info(mibs_path)
        message_dispatcher = MsgAndPduDispatcher(instrum_controller)
        return SnmpEngine(msgAndPduDsp=message_dispatcher)
