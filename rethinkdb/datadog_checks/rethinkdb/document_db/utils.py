# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Miscellaneous utilities.
"""
import datetime as dt
from typing import Any, Mapping, Sequence

from datadog_checks.base.utils.db.utils import normalize_datetime


def lookup_dotted(dct, path):
    # type: (Mapping, str) -> Any
    """
    Given a mapping and a dotted path `key1.key2...keyN`, return the item at `dct[key1][key2]...[keyN]`.

    Raises `ValueError` if an issue is encountered while traversing `path`.
    """
    if not path:
        return dct

    keys = [key for key in reversed(path.split('.'))]
    value = dct

    while keys:
        if not isinstance(value, Mapping):
            raise ValueError(
                'followed path {!r} with remaining keys {!r}, but value {!r} is not a mapping'.format(path, keys, value)
            )

        key = keys.pop()

        try:
            value = value[key]
        except KeyError as exc:
            raise ValueError('Failed to retrieve key {!r} on value {!r}: {!r}'.format(key, value, exc))

    return value


def dotted_join(values):
    # type: (Sequence[str]) -> str
    return '.'.join(filter(None, values))


def to_time_elapsed(datetime):
    # type: (dt.datetime) -> float
    datetime = normalize_datetime(datetime)
    elapsed = dt.datetime.now(datetime.tzinfo) - datetime
    return elapsed.total_seconds()
