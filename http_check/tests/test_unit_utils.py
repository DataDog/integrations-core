# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import mock
import pytest
import socks

from datadog_checks.dev import temp_dir
from datadog_checks.http_check.utils import _get_ca_certs_paths, get_ca_certs_path, parse_proxy_url


def test_get_ca_certs_path():
    with mock.patch('datadog_checks.http_check.utils._get_ca_certs_paths') as gp:
        # no certs found
        gp.return_value = []
        assert get_ca_certs_path() is None
        # one cert file was found
        # let's avoid creating a real file just for the sake of mocking a cert
        # and use __file__ instead
        gp.return_value = [__file__]
        assert get_ca_certs_path() == __file__


def test__get_ca_certs_paths_ko():
    """
    When `embedded` folder is not found, it should raise OSError
    """
    with pytest.raises(OSError):
        _get_ca_certs_paths()


def test__get_ca_certs_paths(embedded_dir):
    with mock.patch('datadog_checks.http_check.utils.os.path.dirname') as dirname:
        # create a tmp `embedded` folder
        with temp_dir() as tmp:
            target = os.path.join(tmp, embedded_dir)
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


def test_parse_proxy_url():
    result = parse_proxy_url("socks5://user:password@host:123")
    assert {
        'proxy_type': socks.SOCKS5,
        'addr': 'host',
        'port': 123,
        'rdns': False,
        'username': 'user',
        'password': 'password',
    } == result

    result = parse_proxy_url("socks5h://host:123")
    assert {
        'proxy_type': socks.SOCKS5,
        'addr': 'host',
        'port': 123,
        'rdns': True,
        'username': None,
        'password': None,
    } == result

    result = parse_proxy_url("socks4://host:123")
    assert {
        'proxy_type': socks.SOCKS4,
        'addr': 'host',
        'port': 123,
        'rdns': False,
        'username': None,
        'password': None,
    } == result

    try:
        assert not parse_proxy_url("/proxy.host/1234")
    except ValueError as e:
        assert e.args == ('unsupported proxy scheme: /proxy.host/1234',)

    try:
        assert not parse_proxy_url("http://:1234")
    except ValueError as e:
        assert e.args == ('Empty host component for proxy: http://:1234',)

    result = parse_proxy_url("http://localhost")
    assert {
        'proxy_type': socks.HTTP,
        'addr': 'localhost',
        'port': 8080,
        'rdns': True,
        'username': None,
        'password': None,
    } == result

    result = parse_proxy_url("socks5a://localhost")
    assert {
        'proxy_type': socks.SOCKS5,
        'addr': 'localhost',
        'port': 1080,
        'rdns': False,
        'username': None,
        'password': None,
    } == result

    try:
        assert not parse_proxy_url("http://localhost:65536")
    except ValueError as e:
        assert e.args == ('Invalid port component for proxy http://localhost:65536, Port out of range 0-65535',)
