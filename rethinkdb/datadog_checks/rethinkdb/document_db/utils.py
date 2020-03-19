# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Miscellaneous utilities.
"""
import datetime as dt
import time
from typing import Any, Mapping, Sequence


def lookup_dotted(dct, path):
    # type: (Mapping, str) -> Any
    """
    Given a mapping and a dotted path `key1.key2...keyN`, return the item at `dct[key1][key2]...[keyN]`.
    """
    keys = [key for key in reversed(path.split('.'))]

    value = dct

    while keys:
        if not isinstance(value, Mapping):  # pragma: no cover
            raise RuntimeError(
                'followed path {!r} with remaining keys {!r}, but value {!r} is not a mapping'.format(path, value, keys)
            )

        key = keys.pop()

        try:
            value = value[key]
        except KeyError as exc:  # pragma: no cover
            raise RuntimeError('Failed to retrieve key {!r} on value {!r}: {!r}'.format(key, value, exc))

    return value


def dotted_join(values, drop_empty=False):
    # type: (Sequence[str], bool) -> str
    if drop_empty:
        values = [value for value in values if value]
    return '.'.join(values)


def to_timestamp(datetime):
    # type: (dt.datetime) -> float
    try:
        return datetime.timestamp()  # type: ignore  # (mypy runs in `--py2` mode.)
    except AttributeError:  # pragma: no cover
        # Python 2.
        return time.mktime(datetime.timetuple())
