# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from collections import defaultdict


class OIDTreeNode(object):

    __slots__ = ('value', 'children')

    def __init__(self):
        self.value = None
        self.children = defaultdict(OIDTreeNode)


class OIDTrie(object):
    """A trie implementation to store OIDs and efficiently match prefixes.

    We use it to do basic MIB-like resolution.
    """

    def __init__(self):
        self._root = OIDTreeNode()

    def set(self, oid, name):
        node = self._root
        for part in oid:
            node = node.children[part]
        node.value = name

    def match(self, oid):
        node = self._root
        matched = []
        value = None
        for part in oid:
            node = node.children.get(part)
            if node is None:
                break
            matched.append(part)
            if node.value is not None:
                value = node.value
        return tuple(matched), value


class OIDResolver(object):
    def __init__(self, mib_view_controller, enforce_constraints):
        self._mib_view_controller = mib_view_controller
        self._resolver = OIDTrie()
        self._index_resolver = defaultdict(dict)
        self._enforce_constraints = enforce_constraints

    def register(self, oid, name):
        """Register a translation from a name to an OID."""
        self._resolver.set(oid, name)

    def register_index(self, name, index, mapping):
        """Register a mapping for index translation."""
        self._index_resolver[name][index] = mapping

    def resolve_oid(self, oid):
        """Resolve an OID to a name and its indexes.

        This first tries to do manual resolution using `self._resolver`, then
        falls back to MIB resolution if that fails.  In the first case it also
        tries to resolve indexes to name if that applies, using
        `self._index_resolver`.
        """
        from .config import to_oid_tuple
        oid, result = oid
        try:
            oid_tuple = to_oid_tuple(oid)
        except ValueError:
            pass
        else:
            prefix, resolved = self._resolver.match(oid_tuple)
            if resolved is not None:
                index_resolver = self._index_resolver.get(resolved)
                indexes = oid_tuple[len(prefix) :]
                if index_resolver:
                    new_indexes = []
                    for i, index in enumerate(indexes, 1):
                        if i in index_resolver:
                            new_indexes.append(index_resolver[i][index])
                        else:
                            new_indexes.append(index)
                    indexes = tuple(new_indexes)
                return resolved, indexes
#        if not self._enforce_constraints:
#            # if enforce_constraints is false, then MIB resolution has not been done yet
#            # so we need to do it manually. We have to specify the mibs that we will need
#            # to resolve the name.
#            oid_to_resolve = hlapi.ObjectIdentity(oid_tuple)
#            result_oid = oid_to_resolve.resolveWithMib(self._mib_view_controller)
        return result.oid, to_oid_tuple(result.oid_index) if result.oid_index else ()
