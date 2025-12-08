# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.clickhouse import utils


@pytest.mark.unit
class TestErrorSanitizer:
    def test_clean(self):
        assert utils.ErrorSanitizer.clean('error..  Stack trace:  \n\n') == 'error.'

    def test_scrub(self):
        sanitizer = utils.ErrorSanitizer('foo')

        assert sanitizer.scrub('foobar') == '**********bar'

    def test_scrub_no_password(self):
        sanitizer = utils.ErrorSanitizer('')

        assert sanitizer.scrub('foobar') == 'foobar'


@pytest.mark.unit
@pytest.mark.parametrize(
    ['version', 'expected'],
    [
        ('25', [25]),
        ('25.1', [25, 1]),
        ('25.1.2', [25, 1, 2]),
        ('25.1.2.3', [25, 1, 2, 3]),
    ]
)
def test_parse_version(version: str, expected: list[int]):
    expected == utils.parse_version(version)
