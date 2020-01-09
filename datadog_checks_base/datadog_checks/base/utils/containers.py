# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from six import iteritems


def freeze(o):
    """
    Freezes any mutable object including dictionaries and lists for hashing.
    Accepts nested dictionaries.
    """
    if isinstance(o, (tuple, list)):
        return tuple(sorted(freeze(e) for e in o))

    if isinstance(o, dict):
        return tuple(sorted((k, freeze(v)) for k, v in iteritems(o)))

    if isinstance(o, (set, frozenset)):
        return tuple(sorted(freeze(e) for e in o))

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
