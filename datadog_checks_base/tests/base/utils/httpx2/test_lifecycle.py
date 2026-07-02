# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

import pytest

from datadog_checks.base.utils import httpx2 as httpx2_module
from datadog_checks.base.utils.httpx2 import HTTPX2Wrapper


def test_close_is_idempotent(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.close()
    http.close()


def test_context_manager(capturing_transport):
    with HTTPX2Wrapper({}, {}, transport=capturing_transport) as http:
        response = http.get('http://example.test/')
    assert response.status_code == 200


def test_request_closes_response_when_adapter_wrap_fails(capturing_transport, monkeypatch):
    closed = []

    def failing_init(self, response):
        # Install the spy at adapter-init time so the close() calls that httpx2 makes
        # while eagerly reading the in-memory MockTransport body during Response.__init__
        # are not counted; only the production guard's close() is observed.
        original_close = response.close
        response.close = lambda: (closed.append(True), original_close())[-1]
        raise RuntimeError('boom')

    monkeypatch.setattr(httpx2_module.HTTPX2ResponseAdapter, '__init__', failing_init)

    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with pytest.raises(RuntimeError, match='boom'):
        http.get('http://example.test/')

    assert closed == [True]


def test_module_import_fails_without_httpx2(monkeypatch):
    monkeypatch.setitem(sys.modules, 'httpx2', None)
    monkeypatch.delitem(sys.modules, 'datadog_checks.base.utils.httpx2', raising=False)
    with pytest.raises(ImportError) as exc_info:
        import datadog_checks.base.utils.httpx2  # noqa: F401
    assert exc_info.value.name == 'httpx2'


@pytest.mark.parametrize(
    'instance,expected_cls_name',
    [
        pytest.param({'use_httpx2': True}, 'HTTPX2Wrapper', id='opt-in'),
        pytest.param({'use_httpx2': False}, 'RequestsWrapper', id='explicit-default'),
        pytest.param({}, 'RequestsWrapper', id='unset-default'),
    ],
)
def test_agentcheck_http_dispatch(instance, expected_cls_name):
    from datadog_checks.base import AgentCheck

    check = AgentCheck('test', {}, [instance])
    try:
        assert type(check.http).__name__ == expected_cls_name
    finally:
        # Read the cached attribute directly (AgentCheck.http is a property that may rebuild).
        http = getattr(check, '_http', None)
        if http is not None:
            close = getattr(http, 'close', None)
            if close is not None:
                close()


def test_teardown_guard_preserves_build_error():
    from datadog_checks.base import AgentCheck

    class BoomCheck(AgentCheck):
        def _build_http_client(self, instance):
            raise RuntimeError('build failed')

    check = BoomCheck('test', {}, [{}])
    with pytest.raises(RuntimeError, match='build failed'):
        try:
            _ = check.http
        finally:
            http = getattr(check, '_http', None)
            if http is not None:
                close = getattr(http, 'close', None)
                if close is not None:
                    close()
