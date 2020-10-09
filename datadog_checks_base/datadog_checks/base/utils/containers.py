# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from six import iteritems


def freeze(o):
    """
    Freezes any mutable object including dictionaries and lists for hashing.
    Accepts nested dictionaries.
    """

    # NOTE: we sort items in containers so that the resulting frozen structure (and its hash) don't depend
    # on the order of those items. In other words: `hash_mutable([1, 2]) == hash_mutable([2, 1])`.
    # So, the sort `key` can be any function that uniquely maps a value to another.
    # We used to use the identify function, i.e. no `key` (or `key=lambda x: x`), but this prevented freezing
    # containers that contain `None` values, since on Python 3 those can't be compared with anything else.
    # The `hash` built-in is a function that uniquely maps values, while being also applicable to all immutable objects.
    # See: https://github.com/DataDog/integrations-core/pull/7763
    key = hash

    if isinstance(o, (tuple, list)):
        return tuple(sorted((freeze(e) for e in o), key=key))

    if isinstance(o, dict):
        return tuple(sorted(((k, freeze(v)) for k, v in iteritems(o)), key=key))

    if isinstance(o, (set, frozenset)):
        return tuple(sorted((freeze(e) for e in o), key=key))

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
