# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime as dt

from datadog_checks.base.utils.time import ensure_aware_datetime


def to_time_elapsed(datetime):
    # type: (dt.datetime) -> float
    datetime = ensure_aware_datetime(datetime)
    elapsed = dt.datetime.now(datetime.tzinfo) - datetime
    return elapsed.total_seconds()
