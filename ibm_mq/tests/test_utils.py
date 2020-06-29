# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.ibm_mq.utils import sanitize_strings

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
    assert expected == sanitize_strings(input_string)
