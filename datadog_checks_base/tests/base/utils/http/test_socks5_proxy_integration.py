# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from requests.exceptions import ConnectTimeout, ProxyError
from six import PY2

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev.ci import running_on_ci, running_on_windows_ci

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(PY2, reason='Test flakes on py2'),
    pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI'),
    pytest.mark.skipif(running_on_ci(), reason='Test is failing on CI'),
]


def test_socks5_proxy(socks5_proxy):
    instance = {'proxy': {'http': 'socks5h://{}'.format(socks5_proxy)}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)
    http.get('http://www.google.com')
    http.get('http://nginx')


def test_no_proxy_single_wildcard(socks5_proxy):
    instance = {'proxy': {'http': 'http://1.2.3.4:567', 'no_proxy': '.foo,bar,*'}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    http.get('http://www.example.org')
    http.get('http://www.example.com')
    if not Platform.is_mac():
        http.get('http://127.0.0.9')


def test_no_proxy_domain(socks5_proxy):
    instance = {'proxy': {'http': 'http://1.2.3.4:567', 'no_proxy': '.google.com,*.example.org,example.com,9'}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    # no_proxy match: .google.com
    http.get('http://www.google.com')

    # no_proxy match: *.example.org
    http.get('http://www.example.org')

    # no_proxy match: example.com
    http.get('http://www.example.com')
    http.get('http://example.com')

    # no_proxy match: 9
    if not Platform.is_mac():
        http.get('http://127.0.0.9')


def test_no_proxy_domain_fail(socks5_proxy):
    instance = {'proxy': {'http': 'http://1.2.3.4:567', 'no_proxy': '.google.com,example.com,example,9'}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    # no_proxy not match: .google.com
    # ".y.com" matches "x.y.com" but not "y.com"
    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://google.com', timeout=1)

    # no_proxy not match: example or example.com
    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://notexample.com', timeout=1)

    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://example.org', timeout=1)

    # no_proxy not match: 9
    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://127.0.0.99', timeout=1)


def test_no_proxy_ip(socks5_proxy):
    instance = {
        'proxy': {
            'http': 'http://1.2.3.4:567',
            'no_proxy': '127.0.0.1,127.0.0.2/32,127.1.0.0/25,127.1.1.0/255.255.255.128,127.1.2.0/0.0.0.127',
        }
    }
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    # no_proxy match: 127.0.0.1
    http.get('http://127.0.0.1', timeout=1)

    if not Platform.is_mac():
        # no_proxy match: 127.0.0.2/32
        http.get('http://127.0.0.2', timeout=1)

        # no_proxy match: IP within 127.1.0.0/25 subnet - cidr bits format
        http.get('http://127.1.0.50', timeout=1)
        http.get('http://127.1.0.100', timeout=1)

        # no_proxy match: IP within 127.1.1.0/255.255.255.128 subnet - net mask format
        http.get('http://127.1.1.50', timeout=1)
        http.get('http://127.1.1.100', timeout=1)

        # no_proxy match: IP within 127.1.2.0/0.0.0.127 subnet - host mask format
        http.get('http://127.1.2.50', timeout=1)
        http.get('http://127.1.2.100', timeout=1)


def test_no_proxy_ip_fail(socks5_proxy):
    instance = {
        'proxy': {
            'http': 'http://1.2.3.4:567',
            'no_proxy': '127.0.0.1,127.0.0.2/32,127.1.0.0/25,127.1.1.0/255.255.255.128,127.1.2.0/0.0.0.127',
        }
    }
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    # no_proxy not match: 127.0.0.1
    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://127.0.0.11', timeout=1)

    # no_proxy not match: 127.0.0.2/32
    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://127.0.0.22', timeout=1)

    # no_proxy not match: IP outside 127.1.0.0/25 subnet - cidr bits format
    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://127.1.0.150', timeout=1)
        http.get('http://127.1.0.200', timeout=1)

    # no_proxy not match: IP outside 127.1.1.0/255.255.255.128 subnet - net mask format
    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://127.1.1.150', timeout=1)
        http.get('http://127.1.1.200', timeout=1)

    # no_proxy not match: IP outside 127.1.2.0/0.0.0.127 subnet - host mask format
    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://127.1.2.150', timeout=1)
        http.get('http://127.1.2.200', timeout=1)
