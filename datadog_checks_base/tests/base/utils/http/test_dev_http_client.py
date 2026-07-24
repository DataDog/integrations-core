# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the real (non-mock) HTTP client seam in ``datadog_checks.dev.http``.

These live in the base test suite because base's environment installs both ``datadog_checks_base``
(which provides ``create_http_client`` and the agnostic exceptions) and ``datadog_checks_dev`` (which
defines the seam), mirroring the existing ``MockHTTPResponse`` tests in ``test_http_testing.py``.
"""

import json
import socket
import threading
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from datadog_checks.base.utils import http_exceptions
from datadog_checks.dev.http import HTTPStatusError, dev_http_client, http_get, http_post


class _EchoHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        # Keep the test output pristine.
        pass

    def _reply(self, body=b''):
        status = int(self.path.rsplit('/', 1)[1]) if self.path.startswith('/status/') else 200
        payload = json.dumps(
            {
                'method': self.command,
                'path': self.path,
                'headers': {key.lower(): value for key, value in self.headers.items()},
                'body': body.decode('utf-8'),
            }
        ).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self._reply()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        self._reply(self.rfile.read(length))


@pytest.fixture
def http_server():
    server = HTTPServer(('127.0.0.1', 0), _EchoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield 'http://{}:{}'.format(host, port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _unused_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def test_http_get_reaches_real_server(http_server):
    response = http_get('{}/hello'.format(http_server))

    assert response.status_code == 200
    echoed = response.json()
    assert echoed['method'] == 'GET'
    assert echoed['path'] == '/hello'


def test_http_get_forwards_query_params(http_server):
    response = http_get(http_server, params={'foo': 'bar'})

    assert 'foo=bar' in response.json()['path']


def test_http_get_forwards_headers(http_server):
    response = http_get(http_server, headers={'X-Test': 'value'})

    assert response.json()['headers']['x-test'] == 'value'


def test_http_post_sends_json_body(http_server):
    response = http_post('{}/submit'.format(http_server), json={'key': 'value'})

    echoed = response.json()
    assert echoed['method'] == 'POST'
    assert json.loads(echoed['body']) == {'key': 'value'}
    assert echoed['headers']['content-type'] == 'application/json'


def test_raise_for_status_raises_agnostic_error(http_server):
    response = http_get('{}/status/404'.format(http_server))

    assert response.status_code == 404
    with pytest.raises(http_exceptions.HTTPStatusError):
        response.raise_for_status()


def test_connection_failure_raises_agnostic_error():
    url = 'http://127.0.0.1:{}/'.format(_unused_port())

    with pytest.raises(http_exceptions.HTTPError):
        http_get(url)


def test_dev_http_client_persist_flag():
    assert dev_http_client(persist=True).persist_connections is True
    assert dev_http_client().persist_connections is False


def test_dev_http_client_applies_default_options(http_server):
    client = dev_http_client(headers={'X-Default': 'yes'})

    response = client.get(http_server)

    assert response.json()['headers']['x-default'] == 'yes'


def test_dev_http_client_reuses_connection_when_persistent(http_server):
    client = dev_http_client(persist=True)

    first = client.get('{}/one'.format(http_server))
    second = client.get('{}/two'.format(http_server))

    assert first.status_code == 200
    assert second.status_code == 200


def test_exception_reexports_are_the_base_types():
    from datadog_checks.dev import http as dev_http

    for name in (
        'HTTPError',
        'HTTPRequestError',
        'HTTPStatusError',
        'HTTPTimeoutError',
        'HTTPConnectionError',
        'HTTPInvalidURLError',
        'HTTPSSLError',
    ):
        assert getattr(dev_http, name) is getattr(http_exceptions, name)

    # The imported symbol resolves to the same agnostic type callers would catch.
    assert HTTPStatusError is http_exceptions.HTTPStatusError


def test_unknown_module_attribute_raises():
    from datadog_checks.dev import http as dev_http

    missing_attribute = 'NotARealSymbol'
    with pytest.raises(AttributeError):
        getattr(dev_http, missing_attribute)
