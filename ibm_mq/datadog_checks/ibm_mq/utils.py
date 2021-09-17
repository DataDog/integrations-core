# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from datetime import datetime
from dateutil import tz

from datadog_checks.base import to_string
from datadog_checks.base.utils.common import round_value
from datadog_checks.base.utils.time import get_timestamp


def sanitize_strings(s):
    """
    Sanitize strings from pymqi responses
    """
    s = to_string(s)
    found = s.find('\x00')
    if found >= 0:
        s = s[:found]
    return s.strip()


def calculate_elapsed_time(self, datestamp, timestamp, current_time=None):
    """
    Calculate elapsed time in seconds from IBM MQ queue status date and timestamps
    Expected Timestamp format: %H.%M.%S, e.g. 18.45.20
    Expected Datestamp format: %Y-%m-%d, e.g. 2021-09-15
    https://www.ibm.com/docs/en/ibm-mq/9.2?topic=reference-display-qstatus-display-queue-status#q086260___3
    """

    qm_tz = tz.gettz(self.queue_manager_tz)

    if current_time is None:
        current_time = get_timestamp()
    else:
        current_time = current_time

    if datestamp and timestamp:
        timestamp_str = sanitize_strings(datestamp) + ' ' + sanitize_strings(timestamp) + ' ' + local_tz
        timestamp_posix = time.mktime(datetime.strptime(timestamp_str, '%Y-%m-%d %H.%M.%S %Z').timetuple())
    else:
        return None

    elapsed = round_value(current_time - timestamp_posix)

    return elapsed
