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
    'datestamp,timestamp,time_zone',
    [
        pytest.param('2021-09-08', '19.19.41', 'UTC', id='elapsed a'),
        pytest.param('2020-01-01', '10.25.13', 'America/New_York', id='elapsed b'),
        pytest.param('2021-08-01', '12.00.00', 'Europe/Paris', id='elapsed c'),
    ],
)
def test_calculate_elapsed_time(datestamp, timestamp, time_zone):
    from datetime import datetime

    from dateutil import tz
    from dateutil.tz import UTC

    from datadog_checks.base.utils.time import EPOCH
    from datadog_checks.ibm_mq.utils import calculate_elapsed_time

    current_tz = UTC
    current_dt = datetime.strptime('2021-09-15 18:46:00', '%Y-%m-%d %H:%M:%S')
    current_dt_tz = current_dt.replace(tzinfo=current_tz)
    current_posix = (current_dt_tz - EPOCH).total_seconds()

    param_tz = tz.gettz(time_zone)
    param_dt = datetime.strptime(datestamp + ' ' + timestamp, '%Y-%m-%d %H.%M.%S')
    param_dt_tz = param_dt.replace(tzinfo=param_tz)
    param_posix = (param_dt_tz - EPOCH).total_seconds()

    expected = current_posix - param_posix

    assert expected == calculate_elapsed_time(datestamp, timestamp, time_zone, current_posix)


@pytest.mark.parametrize(
    'datestamp,timestamp,time_zone,valid',
    [
        pytest.param('2020-01-01', '10.25.13', 'Fake/Timezone', False, id='Invalid TZ: Fake/Timezone'),
        pytest.param('2021-08-01', '12.00.00', 'MT', False, id='Invalid TZ: MT'),
        pytest.param('2021-08-01', '12.00.00', 'Etc/UTC', True, id='Valid TZ: Etc/UTC'),
        pytest.param('2020-01-01', '10.25.13', 'America/Denver', True, id='Valid TZ: America/Denver'),
        pytest.param('2021-05-25', '18.48.20', 'Europe/Madrid', True, id='Valid TZ: Europe/Madrid'),
    ],
)
def test_calculate_elapsed_time_valid_tz(datestamp, timestamp, time_zone, valid):
    from datadog_checks.ibm_mq.utils import calculate_elapsed_time

    if not valid:
        with pytest.raises(ValueError):
            calculate_elapsed_time(datestamp, timestamp, time_zone)
    elif valid:
        assert calculate_elapsed_time(datestamp, timestamp, time_zone) is not None


@pytest.mark.parametrize(
    'datestamp,timestamp,timestamp_dst,time_zone,expected',
    [
        pytest.param('2021-11-07', '02.10.00', '01.55.00', 'America/New_York', 4500, id='DST: America/New_York'),
        pytest.param('2021-03-14', '01.50.00', '03.05.00', 'America/Denver', 900, id='DST: America/Denver'),
        pytest.param('2021-03-14', '01.50.00', '03.50.00', 'America/Anchorage', 3600, id='DST: America/Anchorage'),
        pytest.param('2021-03-14', '01.50.00', '02.05.00', 'Pacific/Honolulu', 900, id='Not DST: Pacific/Honolulu'),
        pytest.param('2021-12-31', '18.30.30', '18.45.30', 'America/Chicago', 900, id='Not DST: America/Chicago'),
        pytest.param(
            '2021-02-15',
            '13.45.00',
            '14.00.00',
            'America/Los_Angeles',
            900,
            id='Not DST: America/Los_Angeles',
        ),
    ],
)
def test_calculate_elapsed_time_valid_dst(datestamp, timestamp, timestamp_dst, time_zone, expected):
    from datadog_checks.ibm_mq.utils import calculate_elapsed_time

    assert (
        abs(
            calculate_elapsed_time(datestamp, timestamp, time_zone)
            - calculate_elapsed_time(datestamp, timestamp_dst, time_zone)
        )
        == expected
    )
