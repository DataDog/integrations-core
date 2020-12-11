import datetime as dt

import pytest
import pytz

from datadog_checks.rethinkdb.utils import to_time_elapsed


def test_to_time_elapsed():
    # type: () -> None
    one_day_seconds = 3600 * 24
    assert to_time_elapsed(dt.datetime.now(pytz.utc) - dt.timedelta(days=1)) == pytest.approx(one_day_seconds, abs=1)
