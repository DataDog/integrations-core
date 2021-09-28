# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime

from dateutil import tz

from datadog_checks.base import to_string
from datadog_checks.base.utils.common import round_value
from datadog_checks.base.utils.time import EPOCH, get_timestamp


def sanitize_strings(s):
    """
    Sanitize strings from pymqi responses
    """
    s = to_string(s)
    found = s.find('\x00')
    if found >= 0:
        s = s[:found]
    return s.strip()


def calculate_elapsed_time(datestamp, timestamp, qm_timezone, current_time=None):
    """
    Calculate elapsed time in seconds from IBM MQ queue status date and timestamps
    Expected Timestamp format: %H.%M.%S, e.g. 18.45.20
    Expected Datestamp format: %Y-%m-%d, e.g. 2021-09-15
    https://www.ibm.com/docs/en/ibm-mq/9.2?topic=reference-display-qstatus-display-queue-status#q086260___3
    """
    if qm_timezone is not None:
        qm_tz = tz.gettz(qm_timezone)
        if qm_tz is None or type(qm_tz) == str:
            msg = (
                'Time zone `{}` is not recognized or may be deprecated. '
                'Please specify a valid time zone in IANA/Olson format.'.format(qm_timezone)
            )
            raise ValueError(msg)
    else:
        qm_tz = tz.UTC

    if current_time is None:
        current_time = get_timestamp()
    else:
        current_time = current_time

    """
    1. Construct a datetime object from the IBM MQ timestamp string format
    2. Set the QM time zone on the datetime object.
    3. Calculate the POSIX timestamp in seconds since EPOCH
    """
    if datestamp and timestamp:
        timestamp_str = sanitize_strings(datestamp) + ' ' + sanitize_strings(timestamp)
        timestamp_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H.%M.%S')
        timestamp_tz = timestamp_dt.replace(tzinfo=qm_tz)
        timestamp_posix = (timestamp_tz - EPOCH).total_seconds()
    else:
        return None

    elapsed = round_value(current_time - timestamp_posix)

    return elapsed
