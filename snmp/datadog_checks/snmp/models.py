# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Define our own models and interfaces for dealing with SNMP data.
"""

from typing import Any, Sequence, Tuple, Union

from .exceptions import CouldNotDecodeOID
from .pysnmp_types import ObjectIdentity, ObjectName, ObjectType
from .utils import format_as_oid_string, parse_as_oid_tuple


class OID(object):
    """
    An SNMP object identifier.

    Acts as a lazy facade for various types used by PySNMP to represent OIDs.
    """

    def __init__(self, value):
        # type: (Union[Sequence[int], str, ObjectName, ObjectIdentity, ObjectType]) -> None

        # NOTE: we can't decode `value` just yet, because it may be a PySNMP object that hasn't been resolved yet.
        # Passing such unresolved objects here is actually OK: looking up the MIB name of an OID isn't required to query
        # it from a server. (Eg. we can query '1.3.6.1.2.1.1.2' without saying 'and by the way, this is sysObjectId'.)
        # Anyway, this is why we do lazy decoding, and why '._initialize()' even exists.
        self._raw = value

    def _initialize(self):
        # type: () -> None
        value = self._raw

        try:
            parts = parse_as_oid_tuple(value)
        except CouldNotDecodeOID:
            raise  # Explicitly re-raise this exception.

        self._parts = parts

    def resolve_as_tuple(self):
        # type: () -> Tuple[int, ...]
        self._initialize()
        return self._parts

    def resolve_as_string(self):
        # type: () -> str
        return '.'.join(map(str, self.resolve_as_tuple()))

    def as_object_type(self):
        # type: () -> ObjectType

        # NOTE: if we have a direct reference to a PySNMP instance, return it without resolving.
        # The goal is to avoid any 'SmiError: OID not fully initialized' exceptions due to not-resolved-yet OIDs.
        if isinstance(self._raw, ObjectType):
            return self._raw
        elif isinstance(self._raw, ObjectIdentity):
            return ObjectType(self._raw)

        return ObjectType(ObjectIdentity(self.resolve_as_tuple()))

    def __eq__(self, other):
        # type: (Any) -> bool
        return isinstance(other, OID) and self.resolve_as_tuple() == other.resolve_as_tuple()

    def __repr__(self):
        # type: () -> str
        return 'OID({!r})'.format(self.resolve_as_string())
