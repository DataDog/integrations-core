# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from six import PY2

pytestmark = [pytest.mark.unit, pytest.mark.skipif(PY2, reason='Test only available on Python 3')]


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
    'datestamp,timestamp,expected',
    [
        pytest.param('2021-09-08', '19.19.41', 76518.19, id='elasped 21h'),
        pytest.param('2020-01-01', '10.25.13', 53327386.19, id='elapsed 2y'),
        pytest.param('2021-08-01', '12.00.00', 3386099.19, id='elapsed past'),
    ],
)
def test_calculate_elapsed_time(datestamp, timestamp, expected):
    from datadog_checks.ibm_mq.utils import calculate_elapsed_time

    current_time = float('1631219699.193989')

    assert expected == calculate_elapsed_time(datestamp, timestamp, current_time)
