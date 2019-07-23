# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import re

from .constants import MILLISECOND


def compact_query(query):
    return re.sub(r'\s+', ' ', query.strip())


def positive(*numbers):
    return max(0, *numbers)


def total_time_to_temporal_percent(total_time, scale=MILLISECOND):
    # This is really confusing, sorry.
    #
    # We get the `total_time` in `scale` since the start and we want to compute a percentage.
    # Since the time is monotonically increasing we can't just submit a point-in-time value but
    # rather it needs to be temporally aware, thus we submit the value as a rate.
    #
    # If we submit it as-is, that would be `scale` per second but we need seconds per second
    # since the Agent's check run interval is internally represented as seconds. Hence we divide
    # by 1000, for example, if the `scale` is milliseconds.
    #
    # At this point we have a number that will be no greater than 1 when compared to the last run.
    #
    # To turn it into a percentage we multiply by 100.
    return total_time / scale * 100
