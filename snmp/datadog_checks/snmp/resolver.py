# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from collections import defaultdict
from typing import DefaultDict, Dict, List, Mapping, Optional, Tuple

from .models import OID
from .pysnmp_types import MibViewController, ObjectIdentity


class OIDTreeNode(object):

    __slots__ = ('value', 'children')

    def __init__(self):
        # type: () -> None
        self.value = None  # type: Optional[str]
        self.children = defaultdict(OIDTreeNode)  # type: DefaultDict[int, OIDTreeNode]


class OIDTrie(object):
    """A trie implementation to store OIDs and efficiently match prefixes.

    We use it to do basic MIB-like resolution.
    """

    def __init__(self):
        # type: () -> None
        self._root = OIDTreeNode()

    def set(self, oid, name):
        # type: (OID, str) -> None
        node = self._root
        for part in oid.resolve_as_tuple():
            node = node.children[part]
        node.value = name

    def match(self, oid):
        # type: (OID) -> Tuple[tuple, Optional[str]]
        node = self._root
        matched = []  # type: List[int]
        value = None
        for part in oid.resolve_as_tuple():
            child = node.children.get(part)
            if child is None:
                break
            node = child
            matched.append(part)
            if node.value is not None:
                value = node.value
        return tuple(matched), value


class OIDResolver(object):
    def __init__(self, mib_view_controller, enforce_constraints):
        # type: (MibViewController, bool) -> None
        self._mib_view_controller = mib_view_controller
        self._resolver = OIDTrie()
        self._index_resolver = defaultdict(dict)  # type: DefaultDict[str, Dict[int, Mapping[int, str]]]
        self._enforce_constraints = enforce_constraints

    def register(self, oid, name):
        # type: (OID, str) -> None
        """Register a translation from a name to an OID."""
        self._resolver.set(oid, name)

    def register_index(self, name, index, mapping):
        # type: (str, int, Mapping[int, str]) -> None
        """Register a mapping for index translation."""
        self._index_resolver[name][index] = mapping

    def resolve_oid(self, oid):
        # type: (OID) -> Tuple[str, Tuple[str, ...]]
        """Resolve an OID to a name and its indexes.

        This first tries to do manual resolution using `self._resolver`, then
        falls back to MIB resolution if that fails.  In the first case it also
        tries to resolve indexes to name if that applies, using
        `self._index_resolver`.
        """
        oid_tuple = oid.resolve_as_tuple()
        prefix, resolved = self._resolver.match(oid)

        if resolved is not None:
            index_resolver = self._index_resolver.get(resolved)
            indexes = oid_tuple[len(prefix) :]
            if index_resolver:
                new_indexes = []
                for i, index in enumerate(indexes, 1):
                    if i in index_resolver:
                        new_indexes.append(index_resolver[i][index])
                    else:
                        new_indexes.append(str(index))
                return resolved, tuple(new_indexes)

            return resolved, tuple(str(index) for index in indexes)

        if not self._enforce_constraints:
            # if enforce_constraints is false, then MIB resolution has not been done yet
            # so we need to do it manually. We have to specify the mibs that we will need
            # to resolve the name.
            oid = OID(ObjectIdentity(oid_tuple).resolveWithMib(self._mib_view_controller))

        return oid.get_mib_symbol()
