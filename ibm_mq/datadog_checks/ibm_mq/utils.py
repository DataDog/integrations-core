# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime

from pytz import UTC, UnknownTimeZoneError, timezone

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
        try:
            qm_tz = timezone(qm_timezone)
        except UnknownTimeZoneError:
            msg = 'Timezone `{}` is not recognized. Please specify timezone in Olson format.'.format(qm_timezone)
            raise UnknownTimeZoneError(msg)
    else:
        qm_tz = UTC

    if current_time is None:
        current_time = get_timestamp()
    else:
        current_time = current_time

    '''
    1. Construct a datetime object from the IBM MQ timestamp string format
    2. Localize the datetime object to the QM timezone
    3. Normalize the datetime object to UTC to account for DST
    4. Calculate the POSIX timestamp in seconds since EPOCH
    '''
    if datestamp and timestamp:
        timestamp_str = sanitize_strings(datestamp) + ' ' + sanitize_strings(timestamp)
        timestamp_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H.%M.%S')
        timestamp_dt_loc = qm_tz.localize(timestamp_dt)
        timestamp_dt_norm = (UTC).normalize(timestamp_dt_loc)
        timestamp_posix = (timestamp_dt_norm - EPOCH).total_seconds()
    else:
        return None

    elapsed = round_value(current_time - timestamp_posix)

    return elapsed
