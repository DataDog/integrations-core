# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys
import pytest
import mock

from datadog_checks.utils.common import pattern_filter
from datadog_checks.utils.limiter import Limiter
from datadog_checks.utils.ca_cert import _get_ca_certs_paths, get_ca_certs_path
from datadog_checks.dev import temp_dir


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
            Item('abc'), Item('def'), Item('abcdef')
        ]


class TestLimiter():
    def test_no_uid(self):
        warnings = []
        limiter = Limiter("my_check", "names", 10, warning_func=warnings.append)
        for i in range(0, 10):
            assert limiter.is_reached() is False
        assert limiter.get_status() == (10, 10, False)

        # Reach limit
        assert limiter.is_reached() is True
        assert limiter.get_status() == (11, 10, True)
        assert warnings == ["Check my_check exceeded limit of 10 names, ignoring next ones"]

        # Make sure warning is only sent once
        assert limiter.is_reached() is True
        assert len(warnings) == 1

    def test_with_uid(self):
        warnings = []
        limiter = Limiter("my_check", "names", 10, warning_func=warnings.append)
        for i in range(0, 20):
            assert limiter.is_reached("dummy1") is False
        assert limiter.get_status() == (1, 10, False)

        for i in range(0, 20):
            assert limiter.is_reached("dummy2") is False
        assert limiter.get_status() == (2, 10, False)
        assert len(warnings) == 0

    def test_mixed(self):
        limiter = Limiter("my_check", "names", 10)

        for i in range(0, 20):
            assert limiter.is_reached("dummy1") is False
        assert limiter.get_status() == (1, 10, False)

        for i in range(0, 5):
            assert limiter.is_reached() is False
        assert limiter.get_status() == (6, 10, False)

    def test_reset(self):
        limiter = Limiter("my_check", "names", 10)

        for i in range(1, 20):
            limiter.is_reached("dummy1")
        assert limiter.get_status() == (1, 10, False)

        limiter.reset()
        assert limiter.get_status() == (0, 10, False)
        assert limiter.is_reached("dummy1") is False
        assert limiter.get_status() == (1, 10, False)


@pytest.mark.unit
def test_get_ca_certs_path():
    with mock.patch('datadog_checks.base.utils.ca_cert._get_ca_certs_paths') as gp:
        # no certs found
        gp.return_value = []
        assert get_ca_certs_path() is None
        # one cert file was found
        # let's avoid creating a real file just for the sake of mocking a cert
        # and use __file__ instead
        gp.return_value = [__file__]
        assert get_ca_certs_path() == __file__


@pytest.mark.unit
def test__get_ca_certs_paths_ko():
    """
    When `embedded` folder is not found, it should raise OSError
    """
    with pytest.raises(OSError):
        _get_ca_certs_paths()


@pytest.mark.unit
def test__get_ca_certs_paths():
    with mock.patch('datadog_checks.base.utils.ca_cert.os.path.dirname') as dirname:
        # create a tmp `embedded` folder
        with temp_dir() as tmp:
            target = os.path.join(tmp, 'embedded')
            os.mkdir(target)
            # point `dirname()` there
            dirname.return_value = target

            # tornado not found
            paths = _get_ca_certs_paths()
            assert len(paths) == 2
            assert paths[0].startswith(target)
            assert paths[1] == '/etc/ssl/certs/ca-certificates.crt'

            # mock tornado's presence
            sys.modules['tornado'] = mock.MagicMock(__file__='.')
            paths = _get_ca_certs_paths()
            assert len(paths) == 3
            assert paths[1].endswith('ca-certificates.crt')
            assert paths[2] == '/etc/ssl/certs/ca-certificates.crt'
