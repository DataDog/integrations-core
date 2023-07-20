# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Define our own models and interfaces for dealing with SNMP data.
"""

from typing import List, Optional, Sequence, Tuple, Union  # noqa: F401

from .exceptions import CouldNotDecodeOID, SmiError, UnresolvedOID
from .pysnmp_inspect import object_identity_from_object_type
from .pysnmp_types import MibViewController, ObjectIdentity, ObjectName, ObjectType  # noqa: F401
from .types import MIBSymbol
from .utils import format_as_oid_string, parse_as_oid_tuple


class OID(object):
    """
    An SNMP object identifier.

    Acts as a facade for various types used by PySNMP to represent OIDs.
    """

    def __init__(self, value):
        # type: (Union[Sequence[int], str, ObjectName, ObjectIdentity, ObjectType]) -> None
        parts = None  # type: Optional[Tuple[int, ...]]

        try:
            parts = parse_as_oid_tuple(value)
        except CouldNotDecodeOID:
            raise  # Invalid input.
        except UnresolvedOID:
            if isinstance(value, ObjectType):
                # An unresolved `ObjectType(ObjectIdentity('<MIB>', '<symbol>'))`.
                parts = None
            elif isinstance(value, ObjectIdentity):
                # An unresolved `ObjectIdentity('<MIB>', '<symbol>')`.
                parts = None
            else:  # pragma: no cover
                raise RuntimeError('Unexpectedly treated {!r} as an unresolved OID'.format(value))

        # Resolve the `ObjectIdentity` which we can use to resolve the MIB name of the OID (for metric naming).
        # PySNMP objects may contain MIB information already, so check for them in priority.
        if isinstance(value, ObjectType):
            object_identity = object_identity_from_object_type(value)
        elif isinstance(value, ObjectIdentity):
            object_identity = value
        else:
            # Fallback.
            if parts is None:  # pragma: no cover
                raise RuntimeError('`parts` should have been set')
            object_identity = ObjectIdentity(parts)

        self._parts = parts
        self._object_identity = object_identity  # type: ObjectIdentity

    def resolve(self, mib_view_controller):
        # type: (MibViewController) -> None
        self._object_identity.resolveWithMib(mib_view_controller)
        self._parts = parse_as_oid_tuple(self._object_identity)

    def as_tuple(self):
        # type: () -> Tuple[int, ...]
        if self._parts is None:
            raise UnresolvedOID('OID parts are not available yet')
        return self._parts

    def as_object_type(self):
        # type: () -> ObjectType
        return ObjectType(self._object_identity)

    def get_mib_symbol(self):
        # type: () -> MIBSymbol
        try:
            result = self._object_identity.getMibSymbol()  # type: Tuple[str, str, Sequence[ObjectName]]
        except SmiError as exc:
            raise UnresolvedOID(exc)

        mib, symbol, indexes = result
        prefix = tuple(index.prettyPrint() for index in indexes)

        return MIBSymbol(mib, symbol, prefix)

    def __str__(self):
        # type: () -> str
        return format_as_oid_string(self.as_tuple())

    def __repr__(self):
        # type: () -> str
        return 'OID({!r})'.format(str(self))


class Device:
    """
    Represents an SNMP device from which we can query OIDs.

    :param ip: The IP address of the device.
    :param port: The UDP port on which the device will be queried.
    :param target: An opaque string used by PySNMP to route queries to the device. See `utils.register_device_target()`.
    """

    def __init__(self, ip, port, target):
        # type: (str, int, str) -> None
        self._ip = ip
        self._port = port
        self._target = target

    @property
    def target(self):
        # type: () -> str
        return self._target

    @property
    def tags(self):
        # type: () -> List[str]
        return ['snmp_device:{}'.format(self._ip)]

    def __repr__(self):
        # type: () -> str
        return '<Device ip={!r}, port={}>'.format(self._ip, self._port)
