# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime as dt

from dateutil.tz import UTC
from pymqi.CMQCFC import MQCAMO_START_DATE, MQCAMO_START_TIME

from ..utils import sanitize_strings

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None


class BaseStats(object):
    def __init__(self, raw_message):
        self.start_datetime = self._parse_datetime(raw_message[MQCAMO_START_DATE], raw_message[MQCAMO_START_TIME])

    @staticmethod
    def _parse_datetime(raw_date, raw_time):
        # date might contain extra chars, we only keep 10 first that match the format YYYY-MM-DD
        date = sanitize_strings(raw_date[:10])
        time = sanitize_strings(raw_time)  # date format YYYY-MM-DD

        naive_start_datetime = dt.datetime.strptime('{} {}'.format(date, time), '%Y-%m-%d %H.%M.%S')

        # TODO: Use datadog_checks.base.utils.time.ensure_aware_datetime
        #       when the integration doesn't need to be backward compatible anymore
        #       with agent versions without ensure_aware_datetime.
        #       When doing that, bump the base package in setup.py
        return naive_start_datetime.replace(tzinfo=UTC)
