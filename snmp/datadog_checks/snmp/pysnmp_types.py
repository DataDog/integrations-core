# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Re-export PyASN1/PySNMP types and classes that we use, so that we can access them from a single module.
"""
from typing import Dict

from pyasn1.type.base import Asn1Type
from pyasn1.type.univ import OctetString
from pysnmp import hlapi
from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    usmDESPrivProtocol,
    usmHMACMD5AuthProtocol,
)
from pysnmp.hlapi.asyncore.cmdgen import lcd
from pysnmp.hlapi.transport import AbstractTransportTarget
from pysnmp.proto.rfc1902 import Counter32, Counter64, Gauge32, Integer, Integer32, ObjectName, Opaque, Unsigned32
from pysnmp.smi.builder import DirMibSource, MibBuilder
from pysnmp.smi.exval import endOfMibView, noSuchInstance, noSuchObject
from pysnmp.smi.view import MibViewController

from .types import SNMPType

__all__ = [
    'AbstractTransportTarget',
    'Asn1Type',
    'DirMibSource',
    'CommunityData',
    'ContextData',
    'endOfMibView',
    'hlapi',
    'lcd',
    'MibViewController',
    'noSuchInstance',
    'noSuchObject',
    'ObjectIdentity',
    'ObjectName',
    'ObjectType',
    'OctetString',
    'SnmpEngine',
    'UdpTransportTarget',
    'usmDESPrivProtocol',
    'usmHMACMD5AuthProtocol',
    'UsmUserData',
]

# Additional types that we support but are not part of the SNMP protocol (see RFC 2856).
CounterBasedGauge64, ZeroBasedCounter64 = MibBuilder().importSymbols(
    'HCNUM-TC', 'CounterBasedGauge64', 'ZeroBasedCounter64'
)

PYSNMP_CLASS_NAME_TO_SNMP_TYPE = {
    Counter32.__name__: 'counter32',
    Counter64.__name__: 'counter64',
    CounterBasedGauge64.__name__: 'counter-based-gauge64',
    Gauge32.__name__: 'gauge32',
    Integer.__name__: 'integer',
    Integer32.__name__: 'integer32',
    Opaque.__name__: 'opaque',
    Unsigned32.__name__: 'unsigned32',
    ZeroBasedCounter64.__name__: 'zero-based-counter64',
}  # type: Dict[str, SNMPType]

# Cleanup items we used here but don't want to expose.
del MibBuilder
del Counter32
del Counter64
del CounterBasedGauge64
del Gauge32
del Integer
del Integer32
del Opaque
del Unsigned32
del ZeroBasedCounter64
