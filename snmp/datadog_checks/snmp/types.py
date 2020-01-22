# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Re-export PySNMP types and classes that we use, so that we can access them from a single module.
"""

from pyasn1.type.base import Asn1Type
from pysnmp.hlapi import CommunityData, ContextData, ObjectIdentity, ObjectType, SnmpEngine, UsmUserData
from pysnmp.hlapi.transport import AbstractTransportTarget
from pysnmp.proto.rfc1902 import ObjectName
from pysnmp.smi import builder
from pysnmp.smi.exval import endOfMibView, noSuchInstance, noSuchObject

# Additional types that are not part of the SNMP protocol. cf RFC 2856
CounterBasedGauge64, ZeroBasedCounter64 = builder.MibBuilder().importSymbols(
    'HCNUM-TC', 'CounterBasedGauge64', 'ZeroBasedCounter64'
)

__all__ = [
    'AbstractTransportTarget',
    'Asn1Type',
    'CommunityData',
    'ContextData',
    'CounterBasedGauge64',
    'ObjectIdentity',
    'ObjectName',
    'ObjectType',
    'SnmpEngine',
    'UsmUserData',
    'endOfMibView',
    'noSuchInstance',
    'noSuchObject',
    'ZeroBasedCounter64',
]
