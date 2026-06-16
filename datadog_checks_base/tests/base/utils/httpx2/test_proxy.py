# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import httpx2
import pytest

from datadog_checks.base.utils.httpx2 import (
    PROXY_SETTINGS_DISABLED,
    HTTPX2Wrapper,
    _build_env_proxy_transport,
    _build_proxy_transport,
    _env_no_proxy,
    _env_proxies,
    _ProxyRoutingTransport,
)

AGENT_GET_CONFIG = 'datadog_checks.base.utils.httpx2.datadog_agent.get_config'
GET_ENV_PROXIES = 'datadog_checks.base.utils.httpx2.get_environment_proxies'

PROXY_ENV_VARS = (
    'HTTP_PROXY',
    'HTTPS_PROXY',
    'ALL_PROXY',
    'NO_PROXY',
    'http_proxy',
    'https_proxy',
    'all_proxy',
    'no_proxy',
    'REQUEST_METHOD',
)


@pytest.fixture
def clean_proxy_env(monkeypatch):
    """Strip proxy-related env vars so each test controls the environment it reads."""
    for name in PROXY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _recording_transport(label: str, sink: list[str]) -> httpx2.MockTransport:
    def handler(_request: httpx2.Request) -> httpx2.Response:
        sink.append(label)
        return httpx2.Response(200)

    return httpx2.MockTransport(handler)


def _served_by(
    no_proxy_uris: list[str],
    url: str,
    *,
    env_schemes: set[str] | None = None,
    env_no_proxy: list[str] | None = None,
) -> str:
    """Route one request through _ProxyRoutingTransport with labelled inners; return the inner that served it."""
    sink: list[str] = []
    direct = _recording_transport('direct', sink)
    scheme_transports = {
        'http': _recording_transport('proxy-http', sink),
        'https': _recording_transport('proxy-https', sink),
    }
    routing = _ProxyRoutingTransport(scheme_transports, direct, no_proxy_uris, env_schemes, env_no_proxy)
    routing.handle_request(httpx2.Request('GET', url))
    assert len(sink) == 1
    return sink[0]


# --- options['proxies'] precedence: instance > init_config > agent ---


def test_options_proxies_from_instance():
    with HTTPX2Wrapper({'proxy': {'http': 'http://i:1', 'https': 'https://i:1'}}, {}) as http:
        assert http.options['proxies'] == {'http': 'http://i:1', 'https': 'https://i:1'}


def test_options_proxies_from_init_config():
    with HTTPX2Wrapper({}, {'proxy': {'http': 'http://ic:2'}}) as http:
        assert http.options['proxies'] == {'http': 'http://ic:2'}


def test_options_proxies_from_agent_config():
    with mock.patch(AGENT_GET_CONFIG, return_value={'http': 'http://a:3', 'no_proxy': 'x,y'}):
        with HTTPX2Wrapper({}, {}) as http:
            assert http.options['proxies'] == {'http': 'http://a:3'}


def test_instance_proxy_overrides_init_and_agent():
    with mock.patch(AGENT_GET_CONFIG, return_value={'http': 'http://a:3'}):
        with HTTPX2Wrapper({'proxy': {'http': 'http://i:1'}}, {'proxy': {'http': 'http://ic:2'}}) as http:
            assert http.options['proxies'] == {'http': 'http://i:1'}


def test_init_config_proxy_overrides_agent():
    with mock.patch(AGENT_GET_CONFIG, return_value={'http': 'http://a:3'}):
        with HTTPX2Wrapper({}, {'proxy': {'http': 'http://ic:2'}}) as http:
            assert http.options['proxies'] == {'http': 'http://ic:2'}


def test_use_agent_proxy_false_skips_agent_config():
    with mock.patch(AGENT_GET_CONFIG, return_value={'http': 'http://a:3'}):
        http = HTTPX2Wrapper({}, {'use_agent_proxy': False})
    assert http.options['proxies'] is None


def test_no_proxy_string_is_split_off_proxies():
    with HTTPX2Wrapper({'proxy': {'http': 'http://i:1', 'no_proxy': 'a.com,b.com;c.com'}}, {}) as http:
        # no_proxy never leaks into options['proxies']; it drives routing instead.
        assert http.options['proxies'] == {'http': 'http://i:1'}
        assert http.no_proxy_uris == ['a.com', 'b.com', 'c.com']  # ';' normalized to ','


# --- skip_proxy ---


def test_skip_proxy_instance_yields_disabled_sentinel():
    http = HTTPX2Wrapper({'proxy': {'http': 'unused'}, 'skip_proxy': True}, {})
    assert http.options['proxies'] == PROXY_SETTINGS_DISABLED


def test_skip_proxy_init_config_yields_disabled_sentinel():
    http = HTTPX2Wrapper({}, {'skip_proxy': True, 'proxy': {'http': 'unused'}})
    assert http.options['proxies'] == PROXY_SETTINGS_DISABLED


def test_legacy_no_proxy_true_maps_to_skip_proxy():
    # no_proxy: true is a legacy alias for skip_proxy in RequestsWrapper (http.py:106).
    with HTTPX2Wrapper({'no_proxy': True}, {}) as http:
        assert http.options['proxies'] == PROXY_SETTINGS_DISABLED


def test_skip_proxy_disables_trust_env_and_builds_no_router():
    with HTTPX2Wrapper({'skip_proxy': True}, {}) as http:
        assert http._client.trust_env is False
        assert not isinstance(http._client._transport, _ProxyRoutingTransport)


def test_injected_transport_keeps_trust_env(clean_proxy_env):
    # No proxy and an injected transport: no router is built, so trust_env stays on for .netrc/SSL_CERT_FILE.
    sink: list[str] = []
    with HTTPX2Wrapper({}, {}, transport=_recording_transport('inj', sink)) as http:
        assert http._client.trust_env is True


# --- a configured proxy routes by scheme and installs the router ---


def test_request_routes_to_matching_scheme_proxy():
    assert _served_by([], 'http://api.example.com/') == 'proxy-http'
    assert _served_by([], 'https://api.example.com/') == 'proxy-https'


def test_proxy_configured_installs_router_and_disables_trust_env():
    with HTTPX2Wrapper({'proxy': {'http': 'http://1.2.3.4:3128'}}, {}) as http:
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


# --- a proxy dict with no usable http/https scheme is treated as unconfigured ---


@pytest.mark.parametrize(
    'proxy',
    [
        pytest.param({'all_proxy': 'http://p:3128'}, id='unknown-scheme-key'),
        pytest.param({'http': ''}, id='empty-scheme-value'),
    ],
)
def test_proxy_with_no_usable_scheme_keeps_trust_env_and_builds_no_router(proxy, clean_proxy_env):
    with mock.patch(AGENT_GET_CONFIG, return_value=None):
        http = HTTPX2Wrapper({'proxy': proxy}, {})
    # No usable proxy URL and no env proxy to fill from: env proxies stay honored and no router is
    # installed, rather than silently disabling both the proxy and HTTP_PROXY/HTTPS_PROXY.
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


def test_build_proxy_transport_skips_direct_allocation_when_no_scheme_usable():
    with mock.patch('datadog_checks.base.utils.httpx2.httpx2.HTTPTransport') as transport_cls:
        result = _build_proxy_transport({'all_proxy': 'http://p:3128'}, None, True, None)
    assert result is None
    assert transport_cls.call_count == 0  # the direct transport must not be built when nothing routes


def test_build_proxy_transport_threads_verify_and_cert_into_inners():
    with mock.patch('datadog_checks.base.utils.httpx2.httpx2.HTTPTransport') as transport_cls:
        _build_proxy_transport({'https': 'http://1.2.3.4:3128'}, None, '/etc/ssl/ca.pem', '/etc/ssl/c.pem')
    calls = transport_cls.call_args_list
    assert calls, 'expected the direct and proxied inner transports to be built'
    assert all(call.kwargs['verify'] == '/etc/ssl/ca.pem' for call in calls)
    assert all(call.kwargs['cert'] == '/etc/ssl/c.pem' for call in calls)


def test_same_proxy_url_for_both_schemes_shares_one_transport():
    transport = _build_proxy_transport({'http': 'http://p:3128', 'https': 'http://p:3128'}, None, True, None)
    assert transport._scheme_transports['http'] is transport._scheme_transports['https']
    transport.close()  # would double-close the shared inner without the id() dedup


def test_proxy_with_only_no_proxy_and_no_env_proxy_is_treated_as_unconfigured(monkeypatch):
    monkeypatch.setattr(GET_ENV_PROXIES, lambda: {})
    with mock.patch(AGENT_GET_CONFIG, return_value=None):
        with HTTPX2Wrapper({'proxy': {'no_proxy': 'internal.corp'}}, {}) as http:
            # No proxy anywhere: stays unconfigured. The no_proxy list is retained (not discarded)
            # so it can apply if an environment proxy is present.
            assert http.options['proxies'] is None
            assert http.no_proxy_uris == ['internal.corp']
            assert http._client.trust_env is True
            assert not isinstance(http._client._transport, _ProxyRoutingTransport)


# --- no_proxy-only config combined with an environment proxy (Option A parity) ---


def test_no_proxy_only_with_env_http_proxy_installs_router_and_disables_trust_env(clean_proxy_env):
    clean_proxy_env.setenv('HTTP_PROXY', 'http://envproxy:3128')
    with mock.patch(AGENT_GET_CONFIG, return_value=None):
        with HTTPX2Wrapper({'proxy': {'no_proxy': 'internal.corp'}}, {}) as http:
            # The wrapper takes over env-proxy resolution so its no_proxy bypass actually applies.
            assert http._client.trust_env is False
            assert isinstance(http._client._transport, _ProxyRoutingTransport)
            assert http.no_proxy_uris == ['internal.corp']


def test_env_proxies_http_only(clean_proxy_env):
    clean_proxy_env.setenv('HTTP_PROXY', 'http://p:1')
    assert _env_proxies() == {'http': 'http://p:1'}


def test_env_proxies_all_proxy_covers_both_schemes(clean_proxy_env):
    clean_proxy_env.setenv('ALL_PROXY', 'http://all:9')
    assert _env_proxies() == {'http': 'http://all:9', 'https': 'http://all:9'}


def test_env_proxies_scheme_specific_beats_all_proxy(clean_proxy_env):
    clean_proxy_env.setenv('HTTPS_PROXY', 'http://https:2')
    clean_proxy_env.setenv('ALL_PROXY', 'http://all:9')
    proxies = _env_proxies()
    assert proxies['https'] == 'http://https:2'
    assert proxies['http'] == 'http://all:9'


def test_env_proxies_lowercase_name_resolves(clean_proxy_env):
    clean_proxy_env.setenv('http_proxy', 'http://low:3')
    assert _env_proxies() == {'http': 'http://low:3'}


def test_env_proxies_empty_without_env(clean_proxy_env):
    assert _env_proxies() == {}


def test_build_env_proxy_transport_separates_instance_and_env_no_proxy_tiers(clean_proxy_env):
    clean_proxy_env.setenv('HTTP_PROXY', 'http://p:1')
    clean_proxy_env.setenv('NO_PROXY', 'env.example')
    transport = _build_env_proxy_transport(None, ['instance.example'], True, None)
    assert isinstance(transport, _ProxyRoutingTransport)
    # Two distinct tiers: instance no_proxy bypasses every proxy; env NO_PROXY only env-filled schemes.
    assert transport._no_proxy_uris == ['instance.example']
    assert transport._env_no_proxy == ['env.example']
    transport.close()


def test_build_env_proxy_transport_preserves_cidr_no_proxy(clean_proxy_env):
    clean_proxy_env.setenv('HTTP_PROXY', 'http://p:1')
    transport = _build_env_proxy_transport(None, ['10.0.0.0/25'], True, None)
    assert '10.0.0.0/25' in transport._no_proxy_uris
    transport.close()


def test_build_env_proxy_transport_none_without_env_proxy(clean_proxy_env, monkeypatch):
    monkeypatch.setattr(GET_ENV_PROXIES, lambda: {})
    assert _build_env_proxy_transport(None, ['internal.corp'], True, None) is None


def test_no_proxy_uris_stored_on_wrapper():
    with HTTPX2Wrapper({'proxy': {'http': 'http://p:1', 'no_proxy': 'a.com,b.com'}}, {}) as http:
        assert http.no_proxy_uris == ['a.com', 'b.com']


def test_no_proxy_uris_none_when_no_proxy_configured():
    with mock.patch(AGENT_GET_CONFIG, return_value=None):
        http = HTTPX2Wrapper({}, {})
    assert http.no_proxy_uris is None


# --- partial proxy block: the environment fills the scheme the instance left unset (Codex follow-up #2) ---


def test_partial_instance_proxy_fills_other_scheme_from_env(clean_proxy_env):
    clean_proxy_env.setenv('HTTPS_PROXY', 'http://envhttps:1')
    with mock.patch(AGENT_GET_CONFIG, return_value=None):
        with HTTPX2Wrapper({'proxy': {'http': 'http://inst:2'}}, {}) as http:
            router = http._client._transport
            assert isinstance(router, _ProxyRoutingTransport)
            assert http._client.trust_env is False
            # http stays on the instance proxy; https is filled from HTTPS_PROXY instead of going direct.
            assert set(router._scheme_transports) == {'http', 'https'}
            assert router._env_schemes == {'https'}


def test_partial_instance_proxy_without_env_omits_other_scheme(clean_proxy_env):
    with mock.patch(AGENT_GET_CONFIG, return_value=None):
        with HTTPX2Wrapper({'proxy': {'http': 'http://inst:2'}}, {}) as http:
            router = http._client._transport
            assert isinstance(router, _ProxyRoutingTransport)
            # No HTTPS_PROXY to fill from: https has no transport, so it falls through to direct.
            assert set(router._scheme_transports) == {'http'}
            assert router._env_schemes == set()


def test_full_instance_proxy_ignores_env(clean_proxy_env):
    clean_proxy_env.setenv('HTTP_PROXY', 'http://envhttp:1')
    clean_proxy_env.setenv('HTTPS_PROXY', 'http://envhttps:1')
    with mock.patch(AGENT_GET_CONFIG, return_value=None):
        with HTTPX2Wrapper({'proxy': {'http': 'http://inst:2', 'https': 'http://inst:3'}}, {}) as http:
            router = http._client._transport
            # Both schemes are instance-configured, so nothing is attributed to the environment.
            assert router._env_schemes == set()


def test_skip_proxy_ignores_env_proxy(clean_proxy_env):
    clean_proxy_env.setenv('HTTP_PROXY', 'http://envhttp:1')
    with HTTPX2Wrapper({'skip_proxy': True}, {}) as http:
        assert http._client.trust_env is False
        assert not isinstance(http._client._transport, _ProxyRoutingTransport)


def test_build_env_proxy_transport_fills_missing_scheme_from_env(clean_proxy_env):
    clean_proxy_env.setenv('HTTPS_PROXY', 'http://envhttps:1')
    transport = _build_env_proxy_transport({'http': 'http://inst:2'}, None, True, None)
    assert set(transport._scheme_transports) == {'http', 'https'}
    assert transport._env_schemes == {'https'}
    transport.close()


def test_build_env_proxy_transport_instance_wins_over_env_per_scheme(clean_proxy_env):
    clean_proxy_env.setenv('HTTP_PROXY', 'http://envhttp:1')
    clean_proxy_env.setenv('HTTPS_PROXY', 'http://envhttps:1')
    transport = _build_env_proxy_transport({'http': 'http://inst:2'}, None, True, None)
    # The instance owns http; only the scheme it left unset is env-filled.
    assert transport._env_schemes == {'https'}
    transport.close()


def test_env_no_proxy_normalizes_semicolons(clean_proxy_env):
    clean_proxy_env.setenv('NO_PROXY', 'a.com;b.com')
    assert _env_no_proxy() == ['a.com', 'b.com']  # ';' normalized to ',', mirroring instance no_proxy


# --- two-tier no_proxy routing: instance no_proxy bypasses all, env NO_PROXY only env-filled schemes ---


def test_env_no_proxy_bypasses_env_filled_scheme():
    assert _served_by([], 'https://internal.corp/', env_schemes={'https'}, env_no_proxy=['internal.corp']) == 'direct'


def test_env_no_proxy_routes_external_host_through_env_proxy():
    served = _served_by([], 'https://external.com/', env_schemes={'https'}, env_no_proxy=['internal.corp'])
    assert served == 'proxy-https'


def test_env_no_proxy_does_not_bypass_instance_scheme():
    # http is instance-configured (not env-filled), so env NO_PROXY must not divert it.
    served = _served_by([], 'http://internal.corp/', env_schemes={'https'}, env_no_proxy=['internal.corp'])
    assert served == 'proxy-http'


def test_explicit_scheme_ignores_env_no_proxy():
    # https here is instance-configured; env NO_PROXY governs only env-filled schemes, so the proxy serves it.
    served = _served_by([], 'https://internal.corp/', env_schemes=set(), env_no_proxy=['internal.corp'])
    assert served == 'proxy-https'


def test_instance_no_proxy_bypasses_every_scheme():
    # Tier-1 instance no_proxy bypasses all proxies regardless of scheme attribution.
    assert _served_by(['internal.corp'], 'https://internal.corp/', env_schemes={'https'}) == 'direct'
    assert _served_by(['internal.corp'], 'http://internal.corp/', env_schemes={'https'}) == 'direct'


def test_unconfigured_scheme_routes_direct():
    sink: list[str] = []
    direct = _recording_transport('direct', sink)
    routing = _ProxyRoutingTransport({'http': _recording_transport('proxy-http', sink)}, direct, None)
    routing.handle_request(httpx2.Request('GET', 'https://api.example.com/'))
    assert sink == ['direct']
