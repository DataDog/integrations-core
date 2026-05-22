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
    http.get('http://example.test/a')
    http.get('http://example.test/b')
    http.post('http://example.test/c', json={'x': 1})
    assert len(captured_requests) == 3


def test_module_import_fails_without_httpx(monkeypatch):
    """Per D4: importing http_httpx without httpx installed raises a clean ImportError."""
    # Force a re-import with httpx missing from sys.modules
    monkeypatch.setitem(sys.modules, 'httpx', None)
    monkeypatch.delitem(sys.modules, 'datadog_checks.base.utils.http_httpx', raising=False)
    with pytest.raises(ImportError):
        import datadog_checks.base.utils.http_httpx  # noqa: F401
