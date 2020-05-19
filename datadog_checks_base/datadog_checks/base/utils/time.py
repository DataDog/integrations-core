# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

from datetime import datetime
from time import time as epoch_offset

from dateutil.tz import UTC

EPOCH = datetime.fromtimestamp(0, UTC)


def get_timestamp(dt=None):
    """
    Returns the number of seconds since the Unix epoch.
    If `dt` is not specified or `None`, the current time in UTC is assumed.
    """
    if dt is None:
        return epoch_offset()

    # TODO: when we drop support for Python 2 switch to:
    # normalize_datetime(dt).timestamp()
    return (normalize_datetime(dt) - EPOCH).total_seconds()


def get_current_datetime(tz=UTC):
    """
    Returns an aware datetime object representing the current time. If `tz` is not specified, UTC is assumed.
    """
    return datetime.now(tz)


def normalize_datetime(dt, default_tz=UTC):
    """
    Ensures that the returned datetime object is not naive.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)

    return dt


__all__ = ['EPOCH', 'UTC', 'get_current_datetime', 'get_timestamp', 'normalize_datetime']
