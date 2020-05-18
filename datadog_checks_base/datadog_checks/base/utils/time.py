# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

from datetime import datetime
from time import time as epoch_offset

import pytz
from six import PY2

UTC = pytz.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


if PY2:

    def get_timestamp(dt=None):
        """
        Returns the number of seconds since the Unix epoch.
        If `dt` is not specified or `None`, the current time in UTC is assumed.
        """
        if dt is None:
            return epoch_offset()

        return (dt - EPOCH).total_seconds()


else:

    def get_timestamp(dt=None):
        """
        Returns the number of seconds since the Unix epoch.
        If `dt` is not specified or `None`, the current time in UTC is assumed.
        """
        if dt is None:
            # NOTE: Although the epoch is platform dependent, it appears to be the same
            # for all platforms we've tested, therefore we use `time.time` for speed.
            #
            # Here is the test:
            #
            #     $ python -c "import time;print(tuple(time.gmtime(0)[:9]))"
            #     (1970, 1, 1, 0, 0, 0, 3, 1, 0)
            #
            # If you can reproduce, add to the following list of tested platforms:
            #
            # - Windows
            # - macOS
            # - Ubuntu
            # - Alpine
            return epoch_offset()

        return normalize_datetime(dt).timestamp()


def get_aware_datetime(dt=None, tz=UTC):
    """
    Returns an aware datetime object. If `dt` is not specified or `None`, the current time in UTC is assumed.
    """
    if dt is None:
        return datetime.now(tz)
    else:
        return normalize_datetime(dt)


def normalize_datetime(dt, default_tz=UTC):
    """
    Ensures that the returned datetime object is not naive.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)

    return dt
