# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Define our own models and interfaces for dealing with SNMP data.
"""

from typing import Any, Sequence, Tuple, Union

from .exceptions import CouldNotDecodeOID
from .pysnmp_types import ObjectIdentity, ObjectName, ObjectType
from .utils import parse_as_oid_tuple


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
