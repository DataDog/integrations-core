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
        key = keys.pop()

        if isinstance(value, Sequence):
            try:
                index = int(key)
            except (TypeError, IndexError):
                raise RuntimeError('Expected key to be an int ')
            try:
                value = value[index]
            except IndexError as exc:
                raise RuntimeError(
                    'Failed to access index {!r} on value {!r} along path {!r}: {!r}'.format(index, value, path, exc)
                )

        elif isinstance(value, Mapping):
            try:
                value = value[key]
            except KeyError as exc:
                raise RuntimeError('Failed to retrieve key {!r} on value {!r}: {!r}'.format(key, value, exc))

        else:
            # We screwed up.
            raise RuntimeError(
                'followed path {!r} with remaining keys {!r}, but value {!r} is not a sequence nor a mapping'.format(
                    path, value, keys
                )
            )

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
        return time.mktime(datetime.now().timetuple())
