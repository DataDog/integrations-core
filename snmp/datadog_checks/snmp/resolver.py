# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Tuple

from .models import OID
from .pysnmp_types import MibViewController, ObjectIdentity


class OIDTreeNode(object):

    __slots__ = ('name', 'children')

    def __init__(self):
        # type: () -> None
        self.name = None  # type: Optional[str]
        self.children = defaultdict(OIDTreeNode)  # type: DefaultDict[int, OIDTreeNode]


class OIDTrie(object):
    """A trie implementation to store OIDs and efficiently match prefixes.

    We use it to do basic MIB-like resolution.
    """

    def __init__(self):
        # type: () -> None
        self._root = OIDTreeNode()

    def set(self, oid, name):
        # type: (Tuple[int, ...], str) -> None
        node = self._root
        for part in oid:
            node = node.children[part]
        node.name = name

    def match(self, oid):
        # type: (Tuple[int, ...]) -> Tuple[Tuple[int, ...], Optional[str]]
        node = self._root
        matched = []
        name = None

        for part in oid:
            child = node.children.get(part)
            if child is None:
                break
            node = child
            matched.append(part)
            if node.name is not None:
                name = node.name

        return tuple(matched), name


class OIDResolver(object):
    """
    Helper for performing resolution of OIDs when tagging table metrics.

    Here's a summary of where this resolver can intervene:

    ```yaml
    metrics:
      - MIB: ...
        table: ...
        symbols:
          - # XXX(1) Direct OID metric resolution.
          - OID: 1.3.6.1.2.1.4.31.1.1.4
            name: ipSystemStatsHCInReceives
        metric_tags:
          - # XXX(2) Column-based tag resolution.
            tag: battery_index
            column:
              OID: 1.3.6.1.4.1.232.6.2.17.2.1.2
              name: cpqHeSysBatteryIndex
          - # XXX(3) Index-based tag resolution.
            tag: ipversion
            index: 1
            mapping:
              0: unknown
              1: ipv4
              2: ipv6
    ```
    """

    def __init__(self, mib_view_controller, enforce_constraints):
        # type: (MibViewController, bool) -> None
        self._mib_view_controller = mib_view_controller
        self._resolver = OIDTrie()
        self._index_resolvers = defaultdict(dict)  # type: DefaultDict[str, Dict[int, Dict[int, str]]]
        self._enforce_constraints = enforce_constraints

    def register(self, oid, name):
        # type: (OID, str) -> None
        """Register a translation from a name to an OID.

        Corresponds to XXX(1) and XXX(2) in the summary listing.
        """
        self._resolver.set(oid.resolve_as_tuple(), name)

    def register_index(self, tag, index, mapping):
        # type: (str, int, Dict[int, str]) -> None
        """Register a mapping for index-based tag translation.

        Corresponds to XXX(3) in the summary listing.
        """
        self._index_resolvers[tag][index] = mapping

    def _resolve_from_mibs(self, oid_tuple, oid):
        # type: (Tuple[int, ...], OID) -> Tuple[str, Tuple[str, ...]]
        if not self._enforce_constraints:
            # if enforce_constraints is false, then MIB resolution has not been done yet
            # so we need to do it manually. We have to specify the mibs that we will need
            # to resolve the name.
            oid = OID(ObjectIdentity(oid_tuple).resolveWithMib(self._mib_view_controller))

        return oid.get_mib_symbol()

    def _resolve_tag_index(self, tail, name):
        # type: (Tuple[int, ...], str) -> Tuple[str, ...]
        mappings_by_index = self._index_resolvers.get(name)

        if mappings_by_index is None:
            # No mapping -> use the OID parts themselves as tag values.
            return tuple(str(part) for part in tail)

        tags = []  # type: List[str]

        for index, part in enumerate(tail, 1):
            if index in mappings_by_index:
                # Default: use mapping to compute tag from index.
                mapping = mappings_by_index[index]
                tag = mapping[part]
                tags.append(tag)
            else:
                # Fallback: use the OID part itself as a tag value.
                tags.append(str(part))

        return tuple(tags)

    def resolve_oid(self, oid):
        # type: (OID) -> Tuple[str, Tuple[str, ...]]
        """Resolve an OID to a name and its indexes.

        This will perform either:
        1. MIB-based resolution, if `oid` doesn't match any registered OID.
        2. Manual resolution, if `oid` matched. In this case, indexes are resolved using any registered mappings.

        Returns
        -------
        name: the name of the metric associated to `oid`.
        tag_index: a sequence of tag values. k-th item in the sequence corresponds to the k-th entry in `metric_tags`.
        """
        oid_tuple = oid.resolve_as_tuple()
        prefix, name = self._resolver.match(oid_tuple)

        if name is None:
            return self._resolve_from_mibs(oid_tuple, oid=oid)

        # Example: oid: (1, 3, 6, 1, 2, 1, 1), prefix: (1, 3, 6, 1) -> tail: (2, 1, 1)
        tail = oid_tuple[len(prefix) :]

        tag_index = self._resolve_tag_index(tail, name=name)
        return name, tag_index
