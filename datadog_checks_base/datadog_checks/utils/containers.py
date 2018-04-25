# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from six import iteritems


def freeze(o):
    """
    Freezes any mutable object including dictionaries and lists for hashing.
    Accepts nested dictionaries.
    """
    if isinstance(o, dict):
        return frozenset((k, freeze(v)) for k, v in iteritems(o))

    if isinstance(o, list):
        return tuple(freeze(v) for v in sorted(o))

    return o


def hash_mutable(m):
    return hash(freeze(m))
