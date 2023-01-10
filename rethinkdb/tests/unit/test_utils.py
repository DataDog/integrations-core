# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime as dt

import pytest

from datadog_checks.base.utils.time import UTC
from datadog_checks.rethinkdb.utils import to_time_elapsed


def test_to_time_elapsed():
    # type: () -> None
    one_day_seconds = 3600 * 24
    assert to_time_elapsed(dt.datetime.now(UTC) - dt.timedelta(days=1)) == pytest.approx(one_day_seconds, abs=1)
