# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Define our own models and interfaces for dealing with SNMP data.
"""
from typing import Any, NoReturn, Optional, Sequence, Tuple, Union

from pyasn1.codec.ber.decoder import decode as pyasn1_decode

from .exceptions import CouldNotDecodeOID
from .pysnmp_types import (
    PYSNMP_CLASS_NAME_TO_SNMP_TYPE,
    Asn1Type,
    ObjectIdentifier,
    ObjectIdentity,
    ObjectName,
    ObjectType,
    endOfMibView,
    noSuchInstance,
    noSuchObject,
)
from .types import SNMPType
from .utils import parse_as_oid_tuple


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

    @property
    def known_snmp_type(self):
        # type: () -> NoReturn
        raise NotImplementedError

    def get_mib_symbol(self):
        # type: () -> Tuple[str, Tuple[str, ...]]
        if not isinstance(self.raw, ObjectIdentity):
            raise NotImplementedError
        _, metric, indexes = self.raw.getMibSymbol()
        return metric, tuple(str(index) for index in indexes)

    def resolve_as_tuple(self):
        # type: () -> Tuple[int, ...]
        self._initialize()  # Trigger decoding of the raw OID object.
        return self._parts

    def resolve_as_string(self):
        # type: () -> str
        return '.'.join(map(str, self.resolve_as_tuple()))

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


class _PySNMPValue(object):
    """
    Wrapper around PySNMP value-like objects.

    Abstracts away any details about the type of the value or its decoding.
    """

    def __init__(self, value):
        # type: (Asn1Type) -> None
        self._value = value

    @property
    def known_snmp_type(self):
        # type: () -> Optional[SNMPType]
        pysnmp_class_name = self._value.__class__.__name__
        try:
            return PYSNMP_CLASS_NAME_TO_SNMP_TYPE[pysnmp_class_name]
        except KeyError:
            # We shouldn't depend on the raw PySNMP class name anywhere in our code, so hide that information.
            return None

    def __int__(self):
        # type: () -> int
        return int(self._value)

    def __float__(self):
        # type: () -> float
        opaque = 'opaque'  # type: SNMPType  # Use type hint to make sure this literal is correct.
        if self.known_snmp_type == opaque:
            decoded, _ = pyasn1_decode(bytes(self._value))
            return float(decoded)
        else:
            return float(self._value)

    def __bool__(self):
        # type: () -> bool
        return not noSuchInstance.isSameTypeWith(self._value) and not noSuchObject.isSameTypeWith(self._value)

    def __nonzero__(self):  # Python 2 compatibility.
        # type: () -> bool
        return self.__bool__()

    def __repr__(self):
        # type: () -> str
        return repr(self._value)

    def __str__(self):
        # type: () -> str
        value = self._value
        if noSuchInstance.isSameTypeWith(value):
            return 'NoSuchInstance'
        elif noSuchObject.isSameTypeWith(value):
            return 'NoSuchObject'
        elif endOfMibView.isSameTypeWith(value):
            return 'EndOfMibView'
        else:
            return value.prettyPrint()


class Value(object):
    """
    Represents an SNMP value, such as a number, a string, an OID, etc.
    """

    def __init__(self, value):
        # type: (Union[ObjectIdentity, Asn1Type]) -> None
        if isinstance(value, ObjectIdentity):
            # OID values (such as obtained when querying `sysObjectID`) may be returned in this form.
            value = OID(value)
        elif isinstance(value, ObjectIdentifier):
            # Another possible type for OID values (such as obtained when querying `sysObjectID`).
            value = OID(tuple(value))
        elif isinstance(value, Asn1Type):
            # Scalar value: a number, a description string, etc.
            value = _PySNMPValue(value)
        else:
            raise RuntimeError('Got unexpected value {!r} of type {}'.format(value, type(value)))

        self._value = value  # type: Union[OID, _PySNMPValue]

    @property
    def known_snmp_type(self):
        # type: () -> Optional[SNMPType]
        return self._value.known_snmp_type

    def __int__(self):
        # type: () -> int
        if isinstance(self._value, OID):
            raise ValueError('OID value is not convertible to int')
        return int(self._value)

    def __float__(self):
        # type: () -> float
        if isinstance(self._value, OID):
            raise ValueError('OID value is not convertible to float')
        return float(self._value)

    def __bool__(self):
        # type: () -> bool
        return bool(self._value)

    def __nonzero__(self):  # Python 2 compatibility.
        # type: () -> bool
        return self.__bool__()

    def __repr__(self):
        # type: () -> str
        return 'Value({!r})'.format(self._value)

    def __str__(self):
        # type: () -> str
        return str(self._value)


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
