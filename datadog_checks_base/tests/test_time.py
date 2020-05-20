# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime

import pytest
from dateutil import tz
from six import PY2

from datadog_checks.base.utils.time import EPOCH, UTC, ensure_aware_datetime, get_current_datetime, get_timestamp

pytestmark = pytest.mark.time


class TestNormalization:
    def test_replace(self):
        now = datetime.now()
        assert now.tzinfo is None

        assert ensure_aware_datetime(now).tzinfo is UTC

    def test_utc(self):
        nyc = tz.gettz('America/New_York')
        now = datetime.now(nyc)

        normalized = ensure_aware_datetime(now)

        assert normalized is now
        assert normalized.tzinfo is nyc


class TestCurrentDatetime:
    # What follows is a workaround for being unable to patch directly:
    # TypeError: can't set attributes of built-in/extension type 'datetime.datetime'

    def test_default_utc(self, mocker):
        datetime_obj = mocker.patch('datadog_checks.base.utils.time.datetime')
        datetime_obj.now = mocker.MagicMock()
        dt = datetime(2020, 2, 2, tzinfo=UTC)
        datetime_obj.now.return_value = dt
        assert get_current_datetime() is dt
        datetime_obj.now.assert_called_once_with(UTC)

    def test_tz(self, mocker):
        datetime_obj = mocker.patch('datadog_checks.base.utils.time.datetime')
        datetime_obj.now = mocker.MagicMock()
        nyc = tz.gettz('America/New_York')
        dt = datetime(2020, 2, 2, tzinfo=nyc)
        datetime_obj.now.return_value = dt
        assert get_current_datetime(nyc) is dt
        datetime_obj.now.assert_called_once_with(nyc)


class TestTimestamp:
    def test_type(self):
        assert isinstance(get_timestamp(), float)

    def test_default(self, mocker):
        time_time = mocker.patch('datadog_checks.base.utils.time.epoch_offset')
        get_timestamp()
        time_time.assert_called_once()

    def test_time_delta(self):
        now = datetime.now()
        expected = (now.replace(tzinfo=UTC) - EPOCH).total_seconds()

        assert get_timestamp(now) == expected


@pytest.mark.skipif(PY2, reason='Using Python 3 features')
class TestConstants:
    def test_epoch(self):
        from datetime import timezone

        assert EPOCH == datetime(1970, 1, 1, tzinfo=timezone.utc)
