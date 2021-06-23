# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from six import iteritems


class _FreezeKey(object):
    # "Why does this class exist?"
    # To freeze and compute hashes or mutable structures, we use sorting as an intermediary step so that the
    # order of items in the container doesn't change the final hash (a property we could call "commutativity").
    # When items in the container are all the same type (eg a list of strings), there is no problem to this.
    # But when the container has items of mixed types, we'd get a `TypeError` on Python 3. (Not on Python 2 though,
    # since comparisons there default to returning `False`.)
    # So this class was introduced to support specific comparison cases that we need to support to fulfill the needs
    # of integrations that use these freeze/hash helpers.

    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        # type: (_FreezeKey) -> bool
        try:
            lt = self.value < other.value
        except TypeError:
            # We're on Python 3, and values are of differing types.
            # Some integrations may using freezing on structures that contain `None`, so we want to support it and
            # use the same behavior than on Python 2, i.e. `None < <anything>` must return `False`...
            if self.value is None:
                # `None < x` -> `True`
                return True
            if other.value is None:
                # `x < None` -> `False`
                return False
            # ...But we let other cases bubble through.
            raise
        else:
            # We're on Python 2, where `a < b` never fails (returns `False` by default), or
            # we're on Python 3 and values have the same type.
            return lt


def _item_freeze_key(item):
    # type: (tuple) -> tuple
    key, value = item
    return (_FreezeKey(key), _FreezeKey(value))


def freeze(o):
    """
    Freezes any mutable object including dictionaries and lists for hashing.
    Accepts nested dictionaries.
    """
    if isinstance(o, (tuple, list)):
        return tuple(sorted((freeze(e) for e in o), key=_FreezeKey))

    if isinstance(o, dict):
        return tuple(sorted(((k, freeze(v)) for k, v in iteritems(o)), key=_item_freeze_key))

    if isinstance(o, (set, frozenset)):
        return tuple(sorted((freeze(e) for e in o), key=_FreezeKey))

    return o


def hash_mutable(m):
    return hash(freeze(m))


def iter_unique(*iterables):
    seen = set()

    for iterable in iterables:
        for item in iterable:
            item_id = hash_mutable(item)

            if item_id in seen:
                continue

            seen.add(item_id)
            yield item
