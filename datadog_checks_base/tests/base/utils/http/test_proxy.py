# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from requests.exceptions import ConnectTimeout, ProxyError

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev import EnvVars


pytestmark = [pytest.mark.unit]


def test_config_default():
    instance = {}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['proxies'] is None
    assert http.no_proxy_uris is None


def test_config_proxy_agent():
    with mock.patch(
        'datadog_checks.base.stubs.datadog_agent.get_config',
        return_value={'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'},
    ):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']


def test_config_proxy_init_config_override():
    with mock.patch(
        'datadog_checks.base.stubs.datadog_agent.get_config',
        return_value={'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'},
    ):
        instance = {}
        init_config = {'proxy': {'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'}}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']


def test_config_proxy_instance_override():
    with mock.patch(
        'datadog_checks.base.stubs.datadog_agent.get_config',
        return_value={'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'},
    ):
        instance = {'proxy': {'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'}}
        init_config = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
        assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']


def test_config_no_proxy_as_list():
    with mock.patch(
        'datadog_checks.base.stubs.datadog_agent.get_config',
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


def test_proxy_env_vars_skip():
    instance = {'skip_proxy': True}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    with EnvVars({'HTTP_PROXY': 'http://1.2.3.4:567'}):
        response = http.get('http://www.google.com')
        response.raise_for_status()

    with EnvVars({'HTTPS_PROXY': 'https://1.2.3.4:567'}):
        response = http.get('https://www.google.com')
        response.raise_for_status()


def test_proxy_env_vars_override_skip_fail():
    instance = {'skip_proxy': True}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    with EnvVars({'HTTP_PROXY': 'http://1.2.3.4:567'}):
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://www.google.com', timeout=1, proxies=None)

    with EnvVars({'HTTPS_PROXY': 'https://1.2.3.4:567'}):
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('https://www.google.com', timeout=1, proxies=None)


def test_proxy_bad():
    instance = {'proxy': {'http': 'http://1.2.3.4:567', 'https': 'https://1.2.3.4:567'}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('http://www.google.com', timeout=1)

    with pytest.raises((ConnectTimeout, ProxyError)):
        http.get('https://www.google.com', timeout=1)


def test_proxy_bad_no_proxy_override_success():
    instance = {
        'proxy': {'http': 'http://1.2.3.4:567', 'https': 'https://1.2.3.4:567', 'no_proxy': 'unused,google.com'}
    }
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    response = http.get('http://www.google.com')
    response.raise_for_status()

    response = http.get('https://www.google.com')
    response.raise_for_status()


def test_no_proxy_uris_coverage():
    http = RequestsWrapper({}, {})

    # Coverage is not smart enough to detect that looping an empty
    # iterable will never occur when gated by `if iterable:`.
    http.no_proxy_uris = mock.MagicMock()

    http.no_proxy_uris.__iter__ = lambda self, *args, **kwargs: iter([])
    http.no_proxy_uris.__bool__ = lambda self, *args, **kwargs: True
    # TODO: Remove with Python 2
    http.no_proxy_uris.__nonzero__ = lambda self, *args, **kwargs: True

    http.get('https://www.google.com')
