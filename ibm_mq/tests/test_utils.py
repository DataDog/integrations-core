# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'input_string,expected',
    [
        pytest.param('abc\x00\x00\x00\x00', 'abc', id='strip_null_chars'),
        pytest.param('   123    ', '123', id='strip_whitespaces'),
        pytest.param('   abc123    \x00\x00\x00\x00', 'abc123', id='strip_whitespaces_and_null_chars'),
        pytest.param(b'abc\x00\x00\x00\x00', 'abc', id='strip_null_chars_bytes'),
        pytest.param(b'   123    ', '123', id='strip_whitespaces_bytes'),
    ],
)
def test_sanitize_strings(input_string, expected):
    from datadog_checks.ibm_mq.utils import sanitize_strings

    assert expected == sanitize_strings(input_string)


@pytest.mark.parametrize(
    'datestamp,timestamp',
    [
        pytest.param('2021-09-08', '19.19.41', id='elapsed a'),
        pytest.param('2020-01-01', '10.25.13', id='elapsed b'),
        pytest.param('2021-08-01', '12.00.00', id='elapsed c'),
    ],
)
def test_calculate_elapsed_time(datestamp, timestamp):
    import time
    from datetime import datetime

    from datadog_checks.ibm_mq.utils import calculate_elapsed_time

    current_tz = time.tzname[time.daylight]
    current_time_str = '2021-09-15 18:46:00' + ' ' + current_tz

    current_timestamp = time.mktime(datetime.strptime(current_time_str, '%Y-%m-%d %H:%M:%S %Z').timetuple())
    expected = current_timestamp - (
        time.mktime(
            datetime.strptime((datestamp + ' ' + timestamp + ' ' + current_tz), '%Y-%m-%d %H.%M.%S %Z').timetuple()
        )
    )

    assert expected == calculate_elapsed_time(datestamp, timestamp, current_timestamp)
