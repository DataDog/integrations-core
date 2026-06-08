# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.httpx2 import HTTPX2Wrapper


def test_unknown_kwarg_typeerror_includes_kwarg_name(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with pytest.raises(TypeError, match='persist'):
        http.get('http://example.test/', persist=True)


def test_unknown_kwarg_typeerror_includes_remediation_for_verify(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with pytest.raises(TypeError) as excinfo:
        http.get('http://example.test/', verify=False)
    message = str(excinfo.value)
    assert 'verify' in message
    assert 'tls_verify' in message


def test_unknown_kwarg_typeerror_includes_remediation_for_persist(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with pytest.raises(TypeError) as excinfo:
        http.get('http://example.test/', persist=True)
    message = str(excinfo.value)
    assert 'persist' in message
    assert 'pools connections' in message


def test_unknown_kwarg_typeerror_includes_remediation_for_cert(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with pytest.raises(TypeError) as excinfo:
        http.get('http://example.test/', cert='/etc/ssl/client.pem')
    message = str(excinfo.value)
    assert 'cert' in message
    assert 'tls_cert' in message
    assert 'tls_private_key' in message


def test_unknown_kwarg_typeerror_includes_remediation_for_proxies(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with pytest.raises(TypeError) as excinfo:
        http.get('http://example.test/', proxies={'http': 'http://proxy:8080'})
    message = str(excinfo.value)
    assert 'proxies' in message
    assert 'proxy support' in message


def test_unknown_kwarg_without_hint_falls_back_gracefully(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with pytest.raises(TypeError) as excinfo:
        http.get('http://example.test/', foobar=1)
    message = str(excinfo.value)
    assert 'foobar' in message
    assert 'tls_verify' not in message
    assert 'pools connections' not in message


def test_unknown_kwarg_multi_lists_each_hint(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with pytest.raises(TypeError) as excinfo:
        http.get('http://example.test/', verify=False, persist=True)
    message = str(excinfo.value)
    assert 'verify' in message
    assert 'persist' in message
    assert 'tls_verify' in message
    assert 'pools connections' in message


def test_stream_kwarg_still_silently_dropped(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.get('http://example.test/', stream=True)
    assert len(captured_requests) == 1
