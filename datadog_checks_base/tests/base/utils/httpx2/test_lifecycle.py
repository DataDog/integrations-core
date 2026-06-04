# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

import pytest

from datadog_checks.base.utils.httpx2 import HTTPX2Wrapper


def test_close_is_idempotent(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.close()
    http.close()


def test_context_manager(capturing_transport):
    with HTTPX2Wrapper({}, {}, transport=capturing_transport) as http:
        response = http.get('http://example.test/')
    assert response.status_code == 200


def test_module_import_fails_without_httpx2(monkeypatch):
    monkeypatch.setitem(sys.modules, 'httpx2', None)
    monkeypatch.delitem(sys.modules, 'datadog_checks.base.utils.httpx2', raising=False)
    with pytest.raises(ImportError, match='httpx2'):
        import datadog_checks.base.utils.httpx2  # noqa: F401
    # After monkeypatch teardown the module must import cleanly again so sibling tests are
    # not affected by a leaked broken import state.
    monkeypatch.undo()
    import datadog_checks.base.utils.httpx2 as restored

    assert hasattr(restored, 'HTTPX2Wrapper')


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
        http = check._http
        if http is not None:
            close = getattr(http, 'close', None)
            if close is not None:
                close()
