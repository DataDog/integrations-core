# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
# TODO import precise_time from base check
from time import time as epoch_offset

from datadog_checks.base import to_string
from datadog_checks.base.utils.common import round_value


def sanitize_strings(s):
    """
    Sanitize strings from pymqi responses
    """
    s = to_string(s)
    found = s.find('\x00')
    if found >= 0:
        s = s[:found]
    return s.strip()


def calculate_elapsed_time(datestamp, timestamp, current_time=None):
    if current_time is None:
        current_time = epoch_offset()
    else:
        current_time = current_time

    if datestamp and timestamp:
        timestamp_str = sanitize_strings(datestamp) + ' ' + sanitize_strings(timestamp)
        timestamp_epoch = datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H.%M.%S').timestamp()
    else:
        return

    elapsed = round_value(current_time - timestamp_epoch)

    return elapsed
