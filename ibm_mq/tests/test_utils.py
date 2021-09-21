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
        pytest.param('2020-01-01', '10.25.13', 'EST', id='elapsed b'),
        pytest.param('2021-08-01', '12.00.00', 'Europe/Paris', id='elapsed c'),
    ],
)
def test_calculate_elapsed_time(datestamp, timestamp, time_zone):
    from datetime import datetime

    from pytz import UTC, timezone

    from datadog_checks.base.utils.time import EPOCH
    from datadog_checks.ibm_mq.utils import calculate_elapsed_time

    current_tz = UTC
    current_dt = datetime.strptime('2021-09-15 18:46:00', '%Y-%m-%d %H:%M:%S')
    current_dt_loc = current_tz.localize(current_dt)
    current_dt_norm = (UTC).normalize(current_dt_loc)
    current_posix = (current_dt_norm - EPOCH).total_seconds()

    param_tz = timezone(time_zone)
    param_dt = datetime.strptime(datestamp + ' ' + timestamp, '%Y-%m-%d %H.%M.%S')
    param_dt_loc = param_tz.localize(param_dt)
    param_dt_norm = (UTC).normalize(param_dt_loc)
    param_posix = (param_dt_norm - EPOCH).total_seconds()

    expected = current_posix - param_posix

    assert expected == calculate_elapsed_time(datestamp, timestamp, time_zone, current_posix)


@pytest.mark.parametrize(
    'datestamp,timestamp,time_zone,valid',
    [
        pytest.param('2020-01-01', '10.25.13', 'Fake/Timezone', False, id='Invalid TZ: Fake/Timezone'),
        pytest.param('2021-08-01', '12.00.00', 'MT', False, id='Invalid TZ: MT'),
        pytest.param('2020-01-01', '10.25.13', 'MST', True, id='Valid TZ: MST'),
        pytest.param('2021-05-25', '18.48.20', 'America/Los_Angeles', True, id='Valid TZ: IANA/Olson format'),
    ],
)
def test_calculate_elapsed_time_valid_tz(datestamp, timestamp, time_zone, valid):
    from pytz import UnknownTimeZoneError

    from datadog_checks.ibm_mq.utils import calculate_elapsed_time

    if not valid:
        with pytest.raises(UnknownTimeZoneError):
            calculate_elapsed_time(datestamp, timestamp, time_zone)
    elif valid:
        assert calculate_elapsed_time(datestamp, timestamp, time_zone) is not None


@pytest.mark.parametrize(
    'datestamp,timestamp,timestamp_dst,time_zone,time_zone_dst',
    [
        pytest.param('2021-11-7', '02.10.00', '01.55.00', 'EST', 'EST5EDT', id='DST: EST vs EST5EDT'),
        pytest.param('2021-03-14', '01.50.00', '02.05.00', 'MST', 'MST7MDT', id='DST: MST vs MST7EDT'),
        pytest.param('2021-12-31', '18.30.30', '18.45.30', 'America/Chicago', 'CST6CDT', id='Not DST: CST vs CST6CDT'),
        pytest.param(
            '2021-02-15',
            '13.45.00',
            '14.00.00',
            'America/Los_Angeles',
            'PST8PDT',
            id='Not DST: America_Los_Angeles vs PST8PDT',
        ),
    ],
)
def test_calculate_elapsed_time_valid_dst(datestamp, timestamp, timestamp_dst, time_zone, time_zone_dst):
    from datadog_checks.ibm_mq.utils import calculate_elapsed_time

    assert (
        abs(
            calculate_elapsed_time(datestamp, timestamp, time_zone)
            - calculate_elapsed_time(datestamp, timestamp_dst, time_zone_dst)
        )
        == 900
    )
