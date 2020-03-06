# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Re-export PyASN1/PySNMP types and classes that we use, so that we can access them from a single module.
"""

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
from pysnmp.proto.rfc1902 import Counter32, Counter64, Gauge32, Integer, Integer32, ObjectName, Unsigned32
from pysnmp.smi.builder import DirMibSource, MibBuilder
from pysnmp.smi.exval import endOfMibView, noSuchInstance, noSuchObject
from pysnmp.smi.view import MibViewController

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
