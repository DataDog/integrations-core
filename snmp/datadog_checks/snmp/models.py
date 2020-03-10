# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Define our own models and interfaces for dealing with SNMP data.
"""

from typing import Any, Sequence, Tuple, Union

from .exceptions import CouldNotDecodeOID
from .pysnmp_types import (
    Asn1Type,
    ObjectIdentifier,
    ObjectIdentity,
    ObjectName,
    ObjectType,
    endOfMibView,
    noSuchInstance,
    noSuchObject,
)
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


class Variable(object):
    """
    An SNMP variable, i.e. an OID associated to a value.
    """

    def __init__(self, oid, value):
        # type: (OID, Union[ObjectIdentity, Asn1Type]) -> None
        if isinstance(value, ObjectIdentity):
            # OID values (such as obtained when querying `sysObjectID`) may be returned in this form.
            value = OID(value)
        elif isinstance(value, ObjectIdentifier):
            # Another possible type for OID values (such as obtained when querying `sysObjectID`).
            value = OID(tuple(value))
        elif isinstance(value, Asn1Type):
            # Scalar value: a number, a description string, etc.
            # NOTE: store as-is for now, but ideally we'd wrap this into an interface we have better control over.
            pass
        else:
            raise RuntimeError('Got unexpected MIB variable value {!r} of type {}'.format(value, type(value)))

        self.oid = oid
        self.value = value  # type: Union[OID, Asn1Type]

    @classmethod
    def from_var_bind(cls, var_bind):
        # type: (Any) -> Variable
        name, value = var_bind
        return cls(oid=OID(name), value=value)

    # NOTE: defined here because the processing of `value` is tightly coupled to the type of the `.value` attribute.
    @staticmethod
    def was_oid_found(value):
        # type: (Union[OID, Asn1Type]) -> bool
        """
        Return whether `value` corresponds to a value indicating that the original OID was found by the SNMP server.
        """
        if isinstance(value, Asn1Type):
            return not noSuchInstance.isSameTypeWith(value) and not noSuchObject.isSameTypeWith(value)

        if not isinstance(value, OID):
            raise RuntimeError('Got unexpected value {!r} of type {}'.format(value, type(value)))

        return True

    def __repr__(self):
        # type: () -> str
        return 'Variable(oid={!r}, value={!r})'.format(self.oid, self.value)

    def __str__(self):
        # type: () -> str
        value = self.value

        if isinstance(value, Asn1Type):
            if noSuchInstance.isSameTypeWith(self.value):
                value = "'NoSuchInstance'"
            elif endOfMibView.isSameTypeWith(self.value):
                value = "'EndOfMibView'"
            else:
                value = value.prettyPrint()
                try:
                    value = str(int(value))
                except (TypeError, ValueError):
                    value = "'{}'".format(value)

        return "('{}', {})".format(self.oid, value)
