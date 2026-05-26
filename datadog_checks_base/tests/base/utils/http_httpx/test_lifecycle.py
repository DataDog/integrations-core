# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

import pytest

from datadog_checks.base.utils.http_httpx import HTTPXWrapper


def test_close_is_idempotent(capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    http.close()
    http.close()


def test_context_manager(capturing_transport):
    with HTTPXWrapper({}, {}, transport=capturing_transport) as http:
        response = http.get('http://example.test/')
    assert response.status_code == 200


def test_single_client_reused_across_requests(capturing_transport, captured_requests):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    client_before_requests = http._client
    http.get('http://example.test/a')
    http.get('http://example.test/b')
    http.post('http://example.test/c', json={'x': 1})
    assert http._client is client_before_requests
    assert len(captured_requests) == 3


def test_module_import_fails_without_httpx(monkeypatch):
    monkeypatch.setitem(sys.modules, 'httpx', None)
    monkeypatch.delitem(sys.modules, 'datadog_checks.base.utils.http_httpx', raising=False)
    with pytest.raises(ImportError):
        import datadog_checks.base.utils.http_httpx  # noqa: F401


def test_agentcheck_http_dispatch_returns_httpx_wrapper():
    from datadog_checks.base import AgentCheck

    check = AgentCheck('test', {}, [{'use_httpx': True}])
    assert isinstance(check.http, HTTPXWrapper)
