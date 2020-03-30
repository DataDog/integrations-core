# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from decimal import ROUND_HALF_DOWN

import mock
import pytest
from six import PY3

from datadog_checks.base.utils.common import (
    ensure_bytes,
    ensure_unicode,
    pattern_filter,
    round_value,
    to_native_string,
    to_string,
)
from datadog_checks.base.utils.containers import iter_unique
from datadog_checks.base.utils.limiter import Limiter
from datadog_checks.base.utils.secrets import SecretsSanitizer


class Item:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self.name == other.name


class TestPatternFilter:
    def test_no_items(self):
        items = []
        whitelist = ['mock']

        assert pattern_filter(items, whitelist=whitelist) == []

    def test_no_patterns(self):
        items = ['mock']

        assert pattern_filter(items) is items

    def test_multiple_matches_whitelist(self):
        items = ['abc', 'def', 'abcdef', 'ghi']
        whitelist = ['abc', 'def']

        assert pattern_filter(items, whitelist=whitelist) == ['abc', 'def', 'abcdef']

    def test_multiple_matches_blacklist(self):
        items = ['abc', 'def', 'abcdef', 'ghi']
        blacklist = ['abc', 'def']

        assert pattern_filter(items, blacklist=blacklist) == ['ghi']

    def test_whitelist_blacklist(self):
        items = ['abc', 'def', 'abcdef', 'ghi']
        whitelist = ['def']
        blacklist = ['abc']

        assert pattern_filter(items, whitelist=whitelist, blacklist=blacklist) == ['def']

    def test_key_function(self):
        items = [Item('abc'), Item('def'), Item('abcdef'), Item('ghi')]
        whitelist = ['abc', 'def']

        assert pattern_filter(items, whitelist=whitelist, key=lambda item: item.name) == [
            Item('abc'),
            Item('def'),
            Item('abcdef'),
        ]


class TestLimiter:
    def test_no_uid(self):
        warning = mock.MagicMock()
        limiter = Limiter("my_check", "names", 10, warning_func=warning)
        for _ in range(0, 10):
            assert limiter.is_reached() is False
        assert limiter.get_status() == (10, 10, False)

        # Reach limit
        assert limiter.is_reached() is True
        assert limiter.get_status() == (11, 10, True)

        # Make sure warning is only sent once
        assert limiter.is_reached() is True
        warning.assert_called_once_with("Check %s exceeded limit of %s %s, ignoring next ones", "my_check", 10, "names")

    def test_with_uid(self):
        warning = mock.MagicMock()
        limiter = Limiter("my_check", "names", 10, warning_func=warning)
        for _ in range(0, 20):
            assert limiter.is_reached("dummy1") is False
        assert limiter.get_status() == (1, 10, False)

        for _ in range(0, 20):
            assert limiter.is_reached("dummy2") is False
        assert limiter.get_status() == (2, 10, False)
        warning.assert_not_called()

    def test_mixed(self):
        limiter = Limiter("my_check", "names", 10)

        for _ in range(0, 20):
            assert limiter.is_reached("dummy1") is False
        assert limiter.get_status() == (1, 10, False)

        for _ in range(0, 5):
            assert limiter.is_reached() is False
        assert limiter.get_status() == (6, 10, False)

    def test_reset(self):
        limiter = Limiter("my_check", "names", 10)

        for _ in range(1, 20):
            limiter.is_reached("dummy1")
        assert limiter.get_status() == (1, 10, False)

        limiter.reset()
        assert limiter.get_status() == (0, 10, False)
        assert limiter.is_reached("dummy1") is False
        assert limiter.get_status() == (1, 10, False)


class TestRounding:
    def test_round_half_up(self):
        assert round_value(3.5) == 4.0

    def test_round_modify_method(self):
        assert round_value(3.5, rounding_method=ROUND_HALF_DOWN) == 3.0

    def test_round_modify_sig_digits(self):
        assert round_value(2.555, precision=2) == 2.560
        assert round_value(4.2345, precision=2) == 4.23
        assert round_value(4.2345, precision=3) == 4.235


class TestContainers:
    def test_iter_unique(self):
        custom_queries = [
            {
                'metric_prefix': 'database',
                'tags': ['test:database'],
                'query': 'SELECT thing1, thing2 FROM TABLE',
                'columns': [{'name': 'database.metric', 'type': 'count'}, {'name': 'tablespace', 'type': 'tag'}],
            },
            {
                'tags': ['test:database'],
                'columns': [{'name': 'tablespace', 'type': 'tag'}, {'name': 'database.metric', 'type': 'count'}],
                'query': 'SELECT thing1, thing2 FROM TABLE',
                'metric_prefix': 'database',
            },
        ]

        assert len(list(iter_unique(custom_queries))) == 1


class TestBytesUnicode:
    @pytest.mark.skipif(PY3, reason="Python 3 does not support explicit bytestring with special characters")
    def test_ensure_bytes_py2(self):
        assert ensure_bytes('éâû') == 'éâû'
        assert ensure_bytes(u'éâû') == 'éâû'

    def test_ensure_bytes(self):
        assert ensure_bytes('qwerty') == b'qwerty'

    def test_ensure_unicode(self):
        assert ensure_unicode('éâû') == u'éâû'
        assert ensure_unicode(u'éâû') == u'éâû'

    def test_to_native_string(self):
        # type: () -> None
        text = u'éâû'
        binary = text.encode('utf-8')
        if PY3:
            assert to_native_string(binary) == text
        else:
            assert to_native_string(binary) == binary

    def test_to_string_deprecated(self):
        # type: () -> None
        with pytest.deprecated_call():
            to_string(b'example')


class TestSecretsSanitizer:
    def test_default(self):
        # type: () -> None
        secret = 's3kr3t'
        sanitizer = SecretsSanitizer()
        assert sanitizer.sanitize(secret) == secret

    def test_sanitize(self):
        # type: () -> None
        secret = 's3kr3t'
        sanitizer = SecretsSanitizer()
        sanitizer.register(secret)
        assert all(letter == '*' for letter in sanitizer.sanitize(secret))

    def test_sanitize_multiple(self):
        # type: () -> None
        pwd1 = 's3kr3t'
        pwd2 = 'admin123'
        sanitizer = SecretsSanitizer()
        sanitizer.register(pwd1)
        sanitizer.register(pwd2)
        message = 'Could not authenticate with password {}, did you try {}?'.format(pwd1, pwd2)
        sanitized = sanitizer.sanitize(message)
        assert pwd1 not in sanitized
        assert pwd2 not in sanitized
