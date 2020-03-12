# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Define our own models and interfaces for dealing with SNMP data.
"""
from typing import Any, Sequence, Tuple, Union

from pyasn1.codec.ber.decoder import decode as pyasn1_decode

from .exceptions import CouldNotDecodeOID
from .pysnmp_types import (
    PYSNMP_COUNTER_CLASSES,
    PYSNMP_GAUGE_CLASSES,
    Asn1Type,
    ObjectIdentifier,
    ObjectIdentity,
    ObjectName,
    ObjectType,
    endOfMibView,
    noSuchInstance,
    noSuchObject,
)
from .utils import format_as_oid_string, parse_as_oid_tuple


class OID(object):
    """
    An SNMP object identifier.

    Acts as a lazy facade for various types used by PySNMP to represent OIDs.
    """

    def __init__(self, value):
        # type: (Union[Sequence[int], str, ObjectName, ObjectIdentity, ObjectType]) -> None
        # NOTE: we can't decode the `value` just yet, because it may be a PySNMP object that hasn't been resolved yet.
        # Using such unresolved objects is generally OK: looking up the MIB name of an OID isn't required to query it
        # from a server. (We can query '1.3.6.1.2.1.1.2' without saying 'and by the way, this is sysObjectId'.)
        # Anyway, this is why we do lazy decoding, and why '._initialize()' even exists.
        self.raw = value

    def _initialize(self):
        # type: () -> None
        value = self.raw

        try:
            parts = parse_as_oid_tuple(value)
        except CouldNotDecodeOID:
            raise  # Explicitly re-raise this exception.

        # Let's make extra sure we didn't mess up.

        if not isinstance(parts, tuple):  # pragma: no cover
            raise RuntimeError(
                'Expected result {!r} of parsing value {!r} to be a tuple, but got {}'.format(parts, value, type(parts))
            )

        for index, part in enumerate(parts):  # pragma: no cover
            if not isinstance(part, int):
                raise RuntimeError(
                    'Expected part {!r} at index {} to be an int, but got {}'.format(part, index, type(part))
                )

        self._parts = parts

    def get_mib_symbol(self):
        # type: () -> Tuple[str, Tuple[str, ...]]
        if not isinstance(self.raw, ObjectIdentity):
            raise NotImplementedError  # pragma: no cover

        _, metric, indexes = self.raw.getMibSymbol()
        return metric, tuple(str(index) for index in indexes)

    def resolve_as_tuple(self):
        # type: () -> Tuple[int, ...]
        self._initialize()
        return self._parts

    def resolve_as_string(self):
        # type: () -> str
        return format_as_oid_string(self.resolve_as_tuple())

    def maybe_resolve_as_object_type(self):
        # type: () -> ObjectType
        # NOTE: if we have a reference to the original PySNMP instance, use it directly and don't resolve it.
        # Otherwise, may trigger an "SmiError: OID not fully initialized" exception.
        if isinstance(self.raw, ObjectType):
            return self.raw
        elif isinstance(self.raw, ObjectIdentity):
            return ObjectType(self.raw)

        return ObjectType(ObjectIdentity(self.resolve_as_tuple()))

    def __eq__(self, other):
        # type: (Any) -> bool
        return isinstance(other, OID) and self.resolve_as_tuple() == other.resolve_as_tuple()

    def __repr__(self):
        # type: () -> str
        return 'OID({!r})'.format(self.resolve_as_string())

    def __str__(self):
        # type: () -> str
        return self.resolve_as_string()


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
        return self._value.__class__.__name__ in PYSNMP_COUNTER_CLASSES

    def is_gauge(self):
        # type: () -> bool
        return self._value.__class__.__name__ in PYSNMP_GAUGE_CLASSES

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
