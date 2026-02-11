# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Verify RequestsWrapper, HTTPXWrapper, and HTTPXResponseAdapter satisfy the HTTP protocols."""

import httpx

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.http_protocol import (
    HTTPClientProtocol,
    HTTPResponseProtocol,
    HTTPSessionLike,
)
from datadog_checks.base.utils.httpx import HTTPXResponseAdapter, HTTPXWrapper


class TestHTTPClientProtocol:
    """Both wrappers satisfy HTTPClientProtocol (structural subtyping)."""

    def test_requests_wrapper_satisfies_http_client_protocol(self):
        wrapper = RequestsWrapper({}, {})
        assert isinstance(wrapper, HTTPClientProtocol)

    def test_httpx_wrapper_satisfies_http_client_protocol(self):
        wrapper = HTTPXWrapper({}, {})
        assert isinstance(wrapper, HTTPClientProtocol)

    def test_wrapper_session_satisfies_httpsession_like(self):
        for wrapper in (RequestsWrapper({}, {}), HTTPXWrapper({}, {})):
            assert isinstance(wrapper.session, HTTPSessionLike)


class TestHTTPResponseProtocol:
    """
    HTTPXResponseAdapter satisfies HTTPResponseProtocol.
    ResponseWrapper (ObjectProxy) is interface-compatible but not runtime-checkable.
    """

    def test_httpx_response_adapter_satisfies_http_response_protocol(self):
        response = httpx.Response(200, content=b'ok')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        assert isinstance(adapter, HTTPResponseProtocol)
