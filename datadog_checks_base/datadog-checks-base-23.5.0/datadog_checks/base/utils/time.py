# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import time
from datetime import datetime
from time import time as epoch_offset

from dateutil.tz import UTC
from six import PY3

from .platform import Platform

EPOCH = datetime.fromtimestamp(0, UTC)


if PY3:
    # use higher precision clock available in Python3
    time_func = time.perf_counter
elif Platform.is_win32():
    # for tiny time deltas, time.time on Windows reports the same value
    # of the clock more than once, causing the computation of response_time
    # to be often 0; let's use time.clock that is more precise.
    time_func = time.clock
else:
    time_func = epoch_offset


def get_precise_time():
    """
    Returns high-precision time suitable for accurate time duration measurements.
    Uses the appropriate precision clock measurement tool depending on Platform and Python version.
    """
    return time_func()


def get_timestamp(dt=None):
    """
    Returns the number of seconds since the Unix epoch.
    If `dt` is not specified or `None`, the current time in UTC is assumed.
    """
    if dt is None:
        # The precision is different between Python 2 and 3
        return epoch_offset()

    # TODO: when we drop support for Python 2 switch to:
    # return ensure_aware_datetime(dt).timestamp()
    return (ensure_aware_datetime(dt) - EPOCH).total_seconds()


def get_current_datetime(tz=UTC):
    """
    Returns an aware datetime object representing the current time. If `tz` is not specified, UTC is assumed.
    """
    return datetime.now(tz)


def ensure_aware_datetime(dt, default_tz=UTC):
    """
    Ensures that the returned datetime object is not naive.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)

    return dt


__all__ = ['EPOCH', 'UTC', 'ensure_aware_datetime', 'get_current_datetime', 'get_precise_time', 'get_timestamp']
