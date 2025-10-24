# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import OrderedDict
from io import BytesIO
from unittest import mock

import pytest
from requests import Response, Session

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev import EnvVars

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module", autouse=True)
def mock_requests_get():
    with mock.patch.object(Session, 'get', autospec=True) as mock_get:
        response = Response()
        response.status_code = 200
        response.raw = BytesIO("Proxied request successful!".encode('utf-8'))
        mock_get.return_value = response
        yield mock_get


def test_config_default():
    instance = {}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['proxies'] is None
    assert http.no_proxy_uris is None


def test_config_proxy_agent():
    with mock.patch(
        'datadog_checks.base.utils.http.datadog_agent.get_config',
        return_value={'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'},
    ):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']


def test_config_proxy_init_config_override():
    with mock.patch(
        'datadog_checks.base.utils.http.datadog_agent.get_config',
        return_value={'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'},
    ):
        instance = {}
        init_config = {'proxy': {'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'}}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']


def test_config_proxy_instance_override():
    with mock.patch(
        'datadog_checks.base.utils.http.datadog_agent.get_config',
        return_value={'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'},
    ):
        instance = {'proxy': {'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'}}
        init_config = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']


def test_config_no_proxy_as_list():
    with mock.patch(
        'datadog_checks.base.utils.http.datadog_agent.get_config',
        return_value={'http': 'http_host', 'https': 'https_host', 'no_proxy': ['uri1', 'uri2', 'uri3', 'uri4']},
    ):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']


def test_config_proxy_skip():
    instance = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}, 'skip_proxy': True}
    init_config = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}}
    http = RequestsWrapper(instance, init_config)

    assert http.options['proxies'] == {'http': '', 'https': ''}
    assert http.no_proxy_uris is None


def test_config_proxy_skip_init_config():
    instance = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}}
    init_config = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}, 'skip_proxy': True}
    http = RequestsWrapper(instance, init_config)

    assert http.options['proxies'] == {'http': '', 'https': ''}
    assert http.no_proxy_uris is None


@pytest.mark.parametrize(
    'url,env_var',
    [('http://www.google.com', 'HTTP_PROXY'), ('https://www.google.com', 'HTTPS_PROXY')],
    ids=['http', 'https'],
)
def test_proxy_env_vars_skip(mock_requests_get: mock.MagicMock, url: str, env_var: str):
    instance = {'skip_proxy': True}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    expected_proxies = {'http': '', 'https': ''}

    with EnvVars({env_var: 'http://1.2.3.4:567'}):
        http.get(url)

        # Since skip is true, we inject empty proxies to the call
        actual_proxies = mock_requests_get.call_args[1]['proxies']
        assert actual_proxies == expected_proxies


@pytest.mark.parametrize(
    'url,env_var',
    [('http://www.google.com', 'HTTP_PROXY'), ('https://www.google.com', 'HTTPS_PROXY')],
    ids=['http', 'https'],
)
def test_proxy_env_vars_override_skip_fail(mock_requests_get: mock.MagicMock, url: str, env_var: str):
    instance = {'skip_proxy': True}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    with EnvVars({env_var: 'http://1.2.3.4:567'}):
        http.get('http://www.google.com', timeout=1, proxies=None)
        actual_proxies = mock_requests_get.call_args[1]['proxies']

        # Even with skip true, we ignore it to call get with the proxies supplied to the get method
        assert actual_proxies is None


@pytest.mark.parametrize(
    "url",
    [
        ('http://www.google.com'),
        ('https://www.google.com'),
    ],
    ids=['http', 'https'],
)
@pytest.mark.parametrize(
    "no_proxies,should_proxy",
    [
        pytest.param({'no_proxy': 'unused,google.com'}, False, id='with_matching_no_proxy'),
        pytest.param({'no_proxy': 'unused,example.com'}, True, id='with_non_matching_no_proxy'),
        pytest.param({}, True, id='without_no_proxy'),
    ],
)
def test_no_proxy_bypass(mock_requests_get: mock.MagicMock, url: str, no_proxies: dict, should_proxy: bool):
    proxies = {'http': 'http://1.2.3.4:567', 'https': 'https://1.2.3.4:567'}
    instance = {'proxy': proxies | no_proxies}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    # Validate that the proxies are injected appropriately
    expected_proxies = proxies if should_proxy else {'http': '', 'https': ''}

    http.get(url)
    actual_proxies = mock_requests_get.call_args[1]['proxies']
    assert actual_proxies == expected_proxies


def test_no_proxy_uris_coverage():
    http = RequestsWrapper({}, {})

    # Coverage is not smart enough to detect that looping an empty
    # iterable will never occur when gated by `if iterable:`.
    http.no_proxy_uris = mock.MagicMock()

    http.no_proxy_uris.__iter__ = lambda self, *args, **kwargs: iter([])
    http.no_proxy_uris.__bool__ = lambda self, *args, **kwargs: True

    http.get('https://www.google.com')


@pytest.mark.parametrize(
    'proxy,expected_proxy,url',
    [
        ({'http': 'socks5h://myproxy'}, {'http': 'socks5h://myproxy'}, 'http://www.example.org'),
        (
            {'http': 'http://1.2.3.4:567', 'no_proxy': '.foo,bar'},
            {
                'http': 'http://1.2.3.4:567',
            },
            'http://www.example.org',
        ),
        ({'http': 'http://1.2.3.4:567', 'no_proxy': '.foo,bar,*'}, {'http': '', 'https': ''}, 'http://www.example.org'),
        (
            {'http': 'http://1.2.3.4:567', 'no_proxy': '.google.com,*.example.org,example.com,9'},
            {'http': '', 'https': ''},
            'http://www.example.org',
        ),
        (
            {'http': 'http://1.2.3.4:567', 'no_proxy': '.google.com,*.example.org,example.com,9'},
            {'http': '', 'https': ''},
            'http://www.google.com',
        ),
        (
            {'http': 'http://1.2.3.4:567', 'no_proxy': '.google.com,*.example.org,example.com,9'},
            {'http': '', 'https': ''},
            'http://example.com',
        ),
        (
            {
                'http': 'http://1.2.3.4:567',
                'no_proxy': '127.0.0.1,127.0.0.2/32,127.1.0.0/25,127.1.1.0/255.255.255.128,127.1.2.0/0.0.0.127',
            },
            {
                'http': 'http://1.2.3.4:567',
            },
            'http://www.example.org',
        ),
    ],
)
def test_proxy_passes_right_params_to_requests(proxy, expected_proxy, url):
    instance = {'proxy': proxy}
    init_config = {}

    http = RequestsWrapper(instance, init_config)

    with mock.patch('requests.Session.get') as mock_get:
        http.get(url)

        call_args = {
            'auth': None,
            'cert': None,
            'headers': OrderedDict(
                [('User-Agent', 'Datadog Agent/0.0.0'), ('Accept', '*/*'), ('Accept-Encoding', 'gzip, deflate')]
            ),
            'proxies': expected_proxy,
            'timeout': (10.0, 10.0),
            'verify': True,
            'allow_redirects': True,
        }
        mock_get.assert_called_with(url, **call_args)
