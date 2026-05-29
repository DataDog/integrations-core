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


def test_module_import_fails_without_httpx2(monkeypatch):
    monkeypatch.setitem(sys.modules, 'httpx2', None)
    monkeypatch.delitem(sys.modules, 'datadog_checks.base.utils.http_httpx', raising=False)
    with pytest.raises(ImportError):
        import datadog_checks.base.utils.http_httpx  # noqa: F401


@pytest.mark.parametrize(
    'instance,expected_cls_name',
    [
        pytest.param({'use_httpx': True}, 'HTTPXWrapper', id='opt-in'),
        pytest.param({'use_httpx': False}, 'RequestsWrapper', id='explicit-default'),
        pytest.param({}, 'RequestsWrapper', id='unset-default'),
    ],
)
def test_agentcheck_http_dispatch(instance, expected_cls_name):
    from datadog_checks.base import AgentCheck

    check = AgentCheck('test', {}, [instance])
    try:
        assert type(check.http).__name__ == expected_cls_name
    finally:
        close = getattr(check.http, 'close', None)
        if close is not None:
            close()
