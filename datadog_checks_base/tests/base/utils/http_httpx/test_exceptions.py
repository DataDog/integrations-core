# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import httpx
import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPRequestError,
    HTTPTimeoutError,
)
from datadog_checks.base.utils.http_httpx import HTTPXWrapper


@pytest.mark.parametrize(
    'raised,expected',
    [
        pytest.param(httpx.ConnectTimeout('boom'), HTTPTimeoutError, id='connect-timeout'),
        pytest.param(httpx.ReadTimeout('slow'), HTTPTimeoutError, id='read-timeout'),
        pytest.param(httpx.PoolTimeout('pool'), HTTPTimeoutError, id='pool-timeout'),
        pytest.param(httpx.ConnectError('refused'), HTTPConnectionError, id='connect-error'),
        pytest.param(httpx.LocalProtocolError('bad'), HTTPRequestError, id='local-protocol-error'),
        pytest.param(httpx.RequestError('generic'), HTTPRequestError, id='request-error'),
    ],
)
def test_request_exception_mapping(raising_transport_factory, raised, expected):
    transport = raising_transport_factory(raised)
    http = HTTPXWrapper({}, {}, transport=transport)
    with pytest.raises(expected):
        http.get('http://example.test/')
