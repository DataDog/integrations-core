# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta, timezone

import pytest

from datadog_checks.base.utils.date import parse_rfc3339


@pytest.mark.parametrize(
    'fraction, microsecond',
    [
        ('', 0),
        ('.0', 0),
        ('.1', 100000),
        ('.123', 123000),
        ('.001', 1000),
        ('.123456', 123456),
        ('.000001', 1),
        ('.123456789', 123456),
        ('.999999999', 999999),
        ('.000000001', 0),
        (',123', 123000),
    ],
)
@pytest.mark.parametrize('suffix, offset', [('Z', 0), ('+05:30', 330), ('-04:30', -270)])
def test_parse_rfc3339_fractional_seconds(fraction: str, microsecond: int, suffix: str, offset: int):
    timestamp = f'2019-02-18T16:00:06{fraction}{suffix}'
    expected = datetime(2019, 2, 18, 16, 0, 6, microsecond, tzinfo=timezone(timedelta(minutes=offset)))

    assert parse_rfc3339(timestamp) == expected
