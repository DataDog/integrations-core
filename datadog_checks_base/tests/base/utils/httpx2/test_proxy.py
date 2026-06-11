# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import httpx2
import pytest

from datadog_checks.base.utils.httpx2 import (
    PROXY_SETTINGS_DISABLED,
    HTTPX2Wrapper,
    _build_proxy_transport,
    _ProxyRoutingTransport,
)

AGENT_GET_CONFIG = 'datadog_checks.base.utils.httpx2.datadog_agent.get_config'


def _recording_transport(label: str, sink: list[str]) -> httpx2.MockTransport:
    def handler(_request: httpx2.Request) -> httpx2.Response:
        sink.append(label)
        return httpx2.Response(200)

    return httpx2.MockTransport(handler)


def _served_by(no_proxy_uris: list[str], url: str) -> str:
    """Route one request through _ProxyRoutingTransport with labelled inners; return the inner that served it."""
    sink: list[str] = []
    direct = _recording_transport('direct', sink)
    scheme_transports = {
        'http': _recording_transport('proxy-http', sink),
        'https': _recording_transport('proxy-https', sink),
    }
    routing = _ProxyRoutingTransport(scheme_transports, direct, no_proxy_uris)
    routing.handle_request(httpx2.Request('GET', url))
    assert len(sink) == 1
    return sink[0]


# --- options['proxies'] precedence: instance > init_config > agent ---


def test_options_proxies_from_instance():
    http = HTTPX2Wrapper({'proxy': {'http': 'http://i:1', 'https': 'https://i:1'}}, {})
    assert http.options['proxies'] == {'http': 'http://i:1', 'https': 'https://i:1'}


def test_options_proxies_from_init_config():
    http = HTTPX2Wrapper({}, {'proxy': {'http': 'http://ic:2'}})
    assert http.options['proxies'] == {'http': 'http://ic:2'}


def test_options_proxies_from_agent_config():
    with mock.patch(AGENT_GET_CONFIG, return_value={'http': 'http://a:3', 'no_proxy': 'x,y'}):
        http = HTTPX2Wrapper({}, {})
    assert http.options['proxies'] == {'http': 'http://a:3'}


def test_instance_proxy_overrides_init_and_agent():
    with mock.patch(AGENT_GET_CONFIG, return_value={'http': 'http://a:3'}):
        http = HTTPX2Wrapper({'proxy': {'http': 'http://i:1'}}, {'proxy': {'http': 'http://ic:2'}})
    assert http.options['proxies'] == {'http': 'http://i:1'}


def test_init_config_proxy_overrides_agent():
    with mock.patch(AGENT_GET_CONFIG, return_value={'http': 'http://a:3'}):
        http = HTTPX2Wrapper({}, {'proxy': {'http': 'http://ic:2'}})
    assert http.options['proxies'] == {'http': 'http://ic:2'}


def test_use_agent_proxy_false_skips_agent_config():
    with mock.patch(AGENT_GET_CONFIG, return_value={'http': 'http://a:3'}):
        http = HTTPX2Wrapper({}, {'use_agent_proxy': False})
    assert http.options['proxies'] is None


def test_no_proxy_string_is_split_off_proxies():
    http = HTTPX2Wrapper({'proxy': {'http': 'http://i:1', 'no_proxy': 'a.com,b.com;c.com'}}, {})
    # no_proxy never leaks into options['proxies']; it drives routing instead.
    assert http.options['proxies'] == {'http': 'http://i:1'}


# --- skip_proxy ---


def test_skip_proxy_instance_yields_disabled_sentinel():
    http = HTTPX2Wrapper({'proxy': {'http': 'unused'}, 'skip_proxy': True}, {})
    assert http.options['proxies'] == PROXY_SETTINGS_DISABLED


def test_skip_proxy_init_config_yields_disabled_sentinel():
    http = HTTPX2Wrapper({}, {'skip_proxy': True, 'proxy': {'http': 'unused'}})
    assert http.options['proxies'] == PROXY_SETTINGS_DISABLED


def test_skip_proxy_disables_trust_env_and_builds_no_router():
    http = HTTPX2Wrapper({'skip_proxy': True}, {})
    assert http._client.trust_env is False
    assert not isinstance(http._client._transport, _ProxyRoutingTransport)


# --- a configured proxy routes by scheme and installs the router ---


def test_request_routes_to_matching_scheme_proxy():
    assert _served_by([], 'http://api.example.com/') == 'proxy-http'
    assert _served_by([], 'https://api.example.com/') == 'proxy-https'


def test_proxy_configured_installs_router_and_disables_trust_env():
    http = HTTPX2Wrapper({'proxy': {'http': 'http://1.2.3.4:3128'}}, {})
    assert http._client.trust_env is False
    assert isinstance(http._client._transport, _ProxyRoutingTransport)


# --- no_proxy host, subdomain, and leading-dot bypass ---


@pytest.mark.parametrize(
    'no_proxy,url,expected',
    [
        pytest.param(['example.com'], 'http://example.com/', 'direct', id='exact-host'),
        pytest.param(['example.com'], 'http://api.example.com/', 'direct', id='subdomain'),
        pytest.param(['.example.com'], 'http://api.example.com/', 'direct', id='leading-dot-subdomain'),
        pytest.param(['.example.com'], 'http://example.com/', 'proxy-http', id='leading-dot-excludes-apex'),
        pytest.param(['*.example.com'], 'http://api.example.com/', 'direct', id='wildcard-subdomain'),
        pytest.param(['example.com'], 'http://other.test/', 'proxy-http', id='unrelated-host'),
    ],
)
def test_no_proxy_host_matching_routes(no_proxy, url, expected):
    assert _served_by(no_proxy, url) == expected


# --- CIDR bypass: bits, netmask, and hostmask forms (ported from RequestsWrapper) ---

CIDR_FORMS = [
    pytest.param('10.0.0.0/25', id='bits'),
    pytest.param('10.0.0.0/255.255.255.128', id='netmask'),
    pytest.param('10.0.0.0/0.0.0.127', id='hostmask'),
]


@pytest.mark.parametrize('cidr', CIDR_FORMS)
def test_cidr_in_range_routes_direct(cidr):
    assert _served_by([cidr], 'http://10.0.0.1/') == 'direct'


@pytest.mark.parametrize('cidr', CIDR_FORMS)
def test_cidr_out_of_range_routes_through_proxy(cidr):
    assert _served_by([cidr], 'http://10.0.0.200/') == 'proxy-http'


# --- a single * disables the proxy for every request ---


def test_single_star_routes_all_direct():
    assert _served_by(['*'], 'http://anything.test/') == 'direct'
    assert _served_by(['*'], 'https://other.example.com/') == 'direct'


# --- no proxy configured: default trust_env so HTTP_PROXY env stays honored ---


def test_no_proxy_configured_keeps_trust_env_default_and_builds_no_router():
    with mock.patch(AGENT_GET_CONFIG, return_value=None):
        http = HTTPX2Wrapper({}, {})
    assert http.options['proxies'] is None
    assert http._client.trust_env is True
    assert not isinstance(http._client._transport, _ProxyRoutingTransport)


# --- _build_proxy_transport decides whether a custom transport is needed ---


def test_build_proxy_transport_returns_none_without_proxy():
    assert _build_proxy_transport(None, None, True, None) is None


def test_build_proxy_transport_returns_none_for_disabled_sentinel():
    assert _build_proxy_transport(PROXY_SETTINGS_DISABLED, None, True, None) is None


def test_build_proxy_transport_builds_router_when_proxy_set():
    transport = _build_proxy_transport({'http': 'http://1.2.3.4:3128'}, None, True, None)
    assert isinstance(transport, _ProxyRoutingTransport)
    transport.close()
