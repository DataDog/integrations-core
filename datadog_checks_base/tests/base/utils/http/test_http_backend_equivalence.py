# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
#
# Behavior equivalence: verify that RequestsWrapper and HTTPXWrapper produce
# identical results for the same HTTP interactions. Any test that fails for only
# one backend reveals a behavioral gap to fix before promoting that backend.
from unittest.mock import patch

import httpx
import pytest
import requests

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.http_httpx import HTTPXWrapper

_BODY = b"line one\nline two\nline three"
_URL = "http://test.example"


def _requests_response(body: bytes, status: int = 200) -> requests.Response:
    r = requests.Response()
    r._content = body
    r._content_consumed = True
    r.status_code = status
    r.encoding = "utf-8"
    return r


def _httpx_transport(body: bytes, status: int = 200) -> httpx.MockTransport:
    def handler(request):
        return httpx.Response(status, content=body)

    return httpx.MockTransport(handler=handler)


@pytest.fixture(params=["requests_backend", "httpx_backend"])
def http_client(request):
    if request.param == "requests_backend":
        with patch.object(requests.Session, "get", return_value=_requests_response(_BODY)):
            yield RequestsWrapper({}, {})
    else:
        yield HTTPXWrapper(httpx.Client(transport=_httpx_transport(_BODY)))


def test_status_code(http_client):
    assert http_client.get(_URL).status_code == 200


def test_body_content(http_client):
    assert http_client.get(_URL).content == _BODY


def test_iter_lines_decodes_to_str(http_client):
    response = http_client.get(_URL)
    assert list(response.iter_lines(decode_unicode=True)) == ["line one", "line two", "line three"]


def test_iter_content_yields_all_bytes(http_client):
    response = http_client.get(_URL)
    assert b"".join(response.iter_content()) == _BODY


def test_context_manager(http_client):
    with http_client.get(_URL) as response:
        assert response.status_code == 200
