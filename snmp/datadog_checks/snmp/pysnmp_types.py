# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Re-export PyASN1/PySNMP types and classes that we use, so that we can access them from a single module.
"""
from typing import Dict

from pyasn1.type.base import Asn1Type
from pyasn1.type.univ import ObjectIdentifier, OctetString
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

# Additional types that are not part of the SNMP protocol (see RFC 2856).
CounterBasedGauge64, ZeroBasedCounter64 = MibBuilder().importSymbols(
    'HCNUM-TC', 'CounterBasedGauge64', 'ZeroBasedCounter64'
)

# Cleanup.
del MibBuilder

__all__ = [
    'AbstractTransportTarget',
    'Asn1Type',
    'DirMibSource',
    'CommunityData',
    'ContextData',
    'CounterBasedGauge64',
    'endOfMibView',
    'hlapi',
    'lcd',
    'MibViewController',
    'noSuchInstance',
    'noSuchObject',
    'ObjectIdentifier',
    'ObjectIdentity',
    'ObjectName',
    'ObjectType',
    'OctetString',
    'SnmpEngine',
    'UdpTransportTarget',
    'usmDESPrivProtocol',
    'usmHMACMD5AuthProtocol',
    'UsmUserData',
    'ZeroBasedCounter64',
    'Counter32',
    'Counter64',
    'Gauge32',
    'Unsigned32',
    'Integer',
    'Integer32',
]

# Ugly hack but couldn't find a cleaner way to map PySNMP value types to SNMP types we support.
# Proper way would be to use the ASN1 method isSameTypeWith but it may wrongfully returns True in the case
# of CounterBasedGauge64 and Counter64 for example.
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
