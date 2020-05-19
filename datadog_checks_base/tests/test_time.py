# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime

import pytest
from dateutil import tz
from six import PY2

from datadog_checks.base.utils.time import EPOCH, UTC, get_current_datetime, get_timestamp, normalize_datetime

pytestmark = pytest.mark.time


def test_timestamp_type():
    assert isinstance(get_timestamp(), float)


class TestNormalization:
    def test_replace(self):
        now = datetime.now()
        assert now.tzinfo is None

        assert normalize_datetime(now).tzinfo is UTC

    def test_utc(self):
        nyc = tz.gettz('America/New_York')
        now = datetime.now(nyc)

        normalized = normalize_datetime(now)

        assert normalized is now
        assert normalized.tzinfo is nyc


class TestCurrentDatetime:
    def test_default_utc(self):
        dt = get_current_datetime()
        now = datetime.now(UTC)

        assert now.tzinfo is UTC
        assert get_timestamp(now) - get_timestamp(dt) < 0.01

    def test_tz(self):
        nyc = tz.gettz('America/New_York')
        dt = get_current_datetime(nyc)
        now = datetime.now(nyc)

        assert now.tzinfo is nyc
        assert get_timestamp(now) - get_timestamp(dt) < 0.01


@pytest.mark.skipif(PY2, reason='Using Python 3 features')
class TestConstants:
    def test_epoch(self):
        from datetime import timezone

        assert EPOCH == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_utc(self):
        from datetime import timezone

        assert UTC.utcoffset(None) == timezone.utc.utcoffset(None)
