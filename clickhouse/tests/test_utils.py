# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.clickhouse.utils import ErrorSanitizer

pytestmark = pytest.mark.unit


class TestErrorSanitizer:
    def test_clean(self):
        assert ErrorSanitizer.clean('error..  Stack trace:  \n\n') == 'error.'

    def test_scrub(self):
        sanitizer = ErrorSanitizer('foo')

        assert sanitizer.scrub('foobar') == '**********bar'

    def test_scrub_no_password(self):
        sanitizer = ErrorSanitizer('')

        assert sanitizer.scrub('foobar') == 'foobar'
