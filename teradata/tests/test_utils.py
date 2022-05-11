# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import pytest

from datadog_checks.teradata.check import TeradataCheck
from datadog_checks.teradata.utils import timestamp_validator

from .common import CHECK_NAME

current_time = int(time.time())


@pytest.mark.parametrize(
    'row, expected, msg',
    [
        pytest.param(
            [current_time, 200.5],
            [current_time, 200.5],
            None,
            id="Valid ts: current timestamp",
        ),
        pytest.param(
            [1648093966, 193.0],
            [],
            "Resource Usage stats are invalid. Row timestamp is more than 1h in the past. "
            "Is `SPMA` Resource Usage Logging enabled?",
            id="Invalid ts: old timestamp",
        ),
        pytest.param(
            [current_time + 800, 300.3],
            [],
            "Row timestamp is more than 10 min in the future. Try checking system time settings.",
            id="Invalid ts: future timestamp",
        ),
        pytest.param(
            ["Not a timestamp", 500],
            [],
            "Returned timestamp `Not a timestamp` is invalid.",
            id="Invalid ts: timestamp not integer",
        ),
    ],
)
def test_timestamp_validator(caplog, instance, row, expected, msg):
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    result = timestamp_validator(check, row)
    assert result == expected
    if msg:
        assert msg in caplog.text
    else:
        assert not caplog.text
