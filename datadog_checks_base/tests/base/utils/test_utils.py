# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from decimal import ROUND_HALF_DOWN

import mock
import pytest

from datadog_checks.base.utils.common import ensure_bytes, ensure_unicode, pattern_filter, round_value, to_native_string
from datadog_checks.base.utils.containers import hash_mutable, hash_mutable_stable, iter_unique
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
    COMPLEX_OBJECT = {
        'url': 'http://localhost:9090/metrics',
        'tags': ['test:tag', 'env:dev'],
        'port': 9090,
        'options': {'timeout': 5, 'retries': 3},
        'none_value': None,
        123: 'integer_key',
    }

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

    @pytest.mark.parametrize(
        'value',
        [
            pytest.param({'x': 'y'}, id='dict'),
            pytest.param({'x': 'y', 'z': None}, id='dict-with-none-value'),
            pytest.param({'x': 'y', None: 't'}, id='dict-with-none-key'),
            pytest.param({'x': ['y', 'z'], 't': 'u'}, id='dict-nest-list'),
            pytest.param(['x', 'y'], id='list'),
            pytest.param(['x', None], id='list-with-none'),
            pytest.param(('x', None), id='tuple-with-none'),
            pytest.param({'x', None}, id='set-with-none'),
        ],
    )
    def test_hash_mutable(self, value):
        h = hash_mutable(value)
        assert isinstance(h, int)

    @pytest.mark.parametrize(
        'value',
        [
            pytest.param(['x', 1], id='mixed-list'),
            pytest.param(['x', [1, 2, 3]], id='mixed-list-nested-1'),
            pytest.param(['x', {'y': 'z'}], id='mixed-list-nested-2'),
            pytest.param(('x', 1), id='mixed-tuple'),
            pytest.param({'x', 1}, id='mixed-set'),
            pytest.param({'x': 1, 2: 'y'}, id='mixed-dict-keys'),
        ],
    )
    def test_hash_mutable_unsupported_mixed_type(self, value):
        """
        Mixed typed containers should be valid as well.
        """
        try:
            hash_mutable(value)
        except TypeError:
            pytest.fail("Mixed typed containers should not raise TypeError.")

    @pytest.mark.parametrize(
        'left, right',
        [
            pytest.param([1, 2], [2, 1], id='top-level'),
            pytest.param({'x': [1, 2]}, {'x': [2, 1]}, id='nested'),
        ],
    )
    def test_hash_mutable_commutative(self, left, right):
        """
        hash_mutable() is expected to return the same hash regardless of the order of items in the container.
        """
        assert hash_mutable(left) == hash_mutable(right)

    # Tests for the hash_mutable_stable just ensure that the hash is always the same
    # No need to cover all usecases since internally we use the same logic as with hash_mutable
    def test_hash_mutable_stable(self):
        expected = "13d8320744fcf8a4c2a1dfe3c4401153b81f5481ddae622374fcf44712198b3c"
        assert hash_mutable_stable(self.COMPLEX_OBJECT) == expected


class TestBytesUnicode:
    def test_ensure_bytes(self):
        assert ensure_bytes('qwerty') == b'qwerty'

    def test_ensure_unicode(self):
        assert ensure_unicode('éâû') == 'éâû'
        assert ensure_unicode('éâû') == 'éâû'

    def test_to_native_string(self):
        # type: () -> None
        text = 'éâû'
        binary = text.encode('utf-8')
        assert to_native_string(binary) == text


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
