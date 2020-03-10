# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Re-export PyASN1/PySNMP types and classes that we use, so that we can access them from a single module.

Also define our own SNMP models and interfaces.
"""

from typing import Any, Sequence, Tuple, Union

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

from .exceptions import CouldNotDecodeOID
from .utils import parse_as_oid_tuple

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


class OID(object):
    """
    An SNMP object identifier.

    Acts as a facade for various types used by PySNMP to represent OIDs.
    """

    def __init__(self, value):
        # type: (Union[Sequence[int], str, ObjectName, ObjectIdentity, ObjectType]) -> None
        try:
            parts = parse_as_oid_tuple(value)
        except CouldNotDecodeOID:
            raise  # Explicitly re-raise this exception.

        # Let's make extra sure we didn't mess up.
        if not isinstance(parts, tuple):
            raise RuntimeError(
                'Expected result {!r} of parsing value {!r} to be a tuple, but got {}'.format(parts, value, type(parts))
            )  # pragma: no cover

        self._parts = parts

    def as_tuple(self):
        # type: () -> Tuple[int, ...]
        return self._parts

    def as_string(self):
        # type: () -> str
        return '.'.join(map(str, self.as_tuple()))

    def __eq__(self, other):
        # type: (Any) -> bool
        return isinstance(other, OID) and self.as_tuple() == other.as_tuple()

    def __repr__(self):
        # type: () -> str
        return 'OID({!r})'.format(self.as_string())
