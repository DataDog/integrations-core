# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Define our own models and interfaces for dealing with SNMP data.
"""
from typing import Any, Optional, Sequence, Set, Tuple, Union

from pyasn1.codec.ber.decoder import decode as pyasn1_decode

from .exceptions import CouldNotDecodeOID, UnresolvedOID, SmiError
from .pysnmp_types import (
    Asn1Type,
    MibViewController,
    ObjectIdentifier,
    ObjectIdentity,
    ObjectName,
    ObjectType,
    endOfMibView,
    noSuchInstance,
    noSuchObject,
)
from .utils import format_as_oid_string, parse_as_oid_tuple

# SNMP value types that we explicitly support.
SNMP_COUNTER_CLASSES = {
    'Counter32',
    'Counter64',
    # Additional types that are not part of the SNMP protocol (see RFC 2856).
    'ZeroBasedCounter64',
}  # type: Set[str]
SNMP_GAUGE_CLASSES = {
    'Gauge32',
    'Integer',
    'Integer32',
    'Unsigned32',
    # Additional types that are not part of the SNMP protocol (see RFC 2856).
    'CounterBasedGauge64',
}  # type: Set[str]


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
            else:
                raise RuntimeError('Unexpectedly treated {!r} as an unresolved OID'.format(value))

        if isinstance(value, ObjectType):
            object_identity = value._ObjectType__args[0]
        elif isinstance(value, ObjectIdentity):
            object_identity = value
        else:
            if parts is None:  # Consistency check.
                raise RuntimeError('`parts` should have been set')
            # IMPORTANT: instantiating an `ObjectIdentity` directly should only be used as a last resort,
            # as otherwise we may lose some metadata, and `.getMibSymbol()` might fail later.
            object_identity = ObjectIdentity(parts)

        self._parts = parts
        self._object_identity = object_identity  # type: ObjectIdentity

    def resolve(self, mib_view_controller):
        # type: (MibViewController) -> None
        if self._parts is None:
            # Consistency check: client code should only call this if they're certain the
            # underlying OID isn't resolved yet.
            raise RuntimeError('Already resolved: {}'.format(self._object_identity))

        self._object_identity.resolveWithMib(mib_view_controller)
        self._parts = parse_as_oid_tuple(self._object_identity)

    def as_tuple(self):
        # type: () -> Tuple[int, ...]
        if self._parts is None:
            raise UnresolvedOID('OID parts are not available given {!r}'.format(self._object_identity))
        return self._parts

    def as_object_type(self):
        # type: () -> ObjectType
        return ObjectType(self._object_identity)

    def get_mib_symbol(self):
        # type: () -> Tuple[str, Tuple[str, ...]]
        try:
            result = self._object_identity.getMibSymbol()  # type: Tuple[str, str, Sequence[ObjectName]]
        except SmiError as exc:
            raise UnresolvedOID(exc)

        _, symbol, indexes = result
        return symbol, tuple(str(index) for index in indexes)

    def __eq__(self, other):
        # type: (Any) -> bool
        return isinstance(other, OID) and self.as_tuple() == other.as_tuple()

    def __str__(self):
        # type: () -> str
        return format_as_oid_string(self.as_tuple())

    def __repr__(self):
        # type: () -> str
        return 'OID({!r})'.format(str(self))


class Value(object):
    """
    Wrapper around PySNMP value-like objects.

    Abstracts away any details about the type of the value or its decoding.
    """

    def __init__(self, value):
        # type: (Asn1Type) -> None
        if isinstance(value, (ObjectIdentifier, ObjectIdentity)):
            # Eg. a result for `sysObjectID`. It's a special case, so wrap around our helper
            # class to make it easier to work with.
            value = OID(value)

        self._value = value  # type: Union[OID, Asn1Type]

    # NOTE: About these class name checks...
    # Ugly hack but couldn't find a cleaner way. Proper way would be to use the ASN.1
    # method `.isSameTypeWith()`, or at least `isinstance()`.
    # But these wrongfully return `True` in some cases, eg:
    # ```python
    # >>> from pysnmp.proto.rfc1902 import Counter64
    # >>> from datadog_checks.snmp.pysnmp_types import CounterBasedGauge64
    # >>> issubclass(CounterBasedGauge64, Counter64)
    # True  # <-- WRONG! (CounterBasedGauge64 values are gauges, not counters.)
    # ````

    def is_counter(self):
        # type: () -> bool
        return self._value.__class__.__name__ in SNMP_COUNTER_CLASSES

    def is_gauge(self):
        # type: () -> bool
        return self._value.__class__.__name__ in SNMP_GAUGE_CLASSES

    def is_opaque(self):
        # type: () -> bool
        # Arbitrary ASN.1 syntax encoded as an octet string.
        # See: http://snmplabs.com/pysnmp/docs/api-reference.html#opaque-type
        return self._value.__class__.__name__ == 'Opaque'

    def __int__(self):
        # type: () -> int
        if isinstance(self._value, OID):
            raise ValueError

        return int(self._value)

    def __float__(self):
        # type: () -> float
        if isinstance(self._value, OID):
            raise ValueError

        if self.is_opaque():
            decoded, _ = pyasn1_decode(bytes(self._value))
            return float(decoded)

        return float(self._value)

    def __bool__(self):
        # type: () -> bool
        if isinstance(self._value, OID):
            return True

        if noSuchInstance.isSameTypeWith(self._value):
            return False

        if noSuchObject.isSameTypeWith(self._value):
            return False

        return True

    def __nonzero__(self):  # Python 2 compatibility.
        # type: () -> bool
        return self.__bool__()

    def __repr__(self):
        # type: () -> str
        return 'Value({!r})'.format(self._value)

    def __str__(self):
        # type: () -> str
        value = self._value

        if isinstance(value, OID):
            return str(value)

        if noSuchInstance.isSameTypeWith(value):
            return 'NoSuchInstance'

        if noSuchObject.isSameTypeWith(value):
            return 'NoSuchObject'

        if endOfMibView.isSameTypeWith(value):
            return 'EndOfMibView'

        return value.prettyPrint()


class Variable(object):
    """
    An SNMP variable, i.e. an OID associated to a value.
    """

    def __init__(self, oid, value):
        # type: (OID, Value) -> None
        self.oid = oid
        self.value = value

    def __repr__(self):
        # type: () -> str
        return 'Variable(oid={!r}, value={!r})'.format(self.oid, self.value)

    def __str__(self):
        # type: () -> str
        return '({}, {})'.format(self.oid, self.value)
