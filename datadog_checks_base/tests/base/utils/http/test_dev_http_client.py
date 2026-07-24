# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the real HTTP client seam across datadog_checks_base and datadog_checks_dev."""

import json
import socket
import threading
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from datadog_checks.base.utils import http_exceptions
from datadog_checks.dev.http import (
    HTTPStatusError,
    dev_http_client,
    http_delete,
    http_get,
    http_head,
    http_patch,
    http_post,
    http_put,
)


class _EchoHandler(BaseHTTPRequestHandler):
    # HTTP/1.1 enables keep-alive so a persistent client reuses one TCP connection across calls.
    protocol_version = 'HTTP/1.1'

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
                # Source port makes keep-alive connection reuse observable.
                'client_port': self.client_address[1],
            }
        ).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length)

    def do_GET(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/final')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self._reply()

    def do_POST(self):
        self._reply(self._read_body())

    def do_PUT(self):
        self._reply(self._read_body())

    def do_PATCH(self):
        self._reply(self._read_body())

    def do_DELETE(self):
        self._reply(self._read_body())

    def do_HEAD(self):
        # HEAD must echo the method via a header and send no body.
        self.send_response(200)
        self.send_header('X-Echo-Method', 'HEAD')
        self.send_header('Content-Length', '0')
        self.end_headers()


@pytest.fixture
def http_server():
    # Use per-connection daemon threads so keep-alive sockets do not block serve_forever.
    server = ThreadingHTTPServer(('127.0.0.1', 0), _EchoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield 'http://{}:{}'.format(host, port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def refused_url():
    # Release a probed ephemeral port so connects are refused quickly and cross-platform.
    # Holding it bound avoids reuse races but makes macOS drop SYNs and time out instead.
    # The loopback reuse window is negligible within this test.
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    yield 'http://127.0.0.1:{}/'.format(port)


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


def test_http_get_forwards_cookies(http_server):
    response = http_get(http_server, cookies={'session': 'abc'})

    assert 'session=abc' in response.json()['headers']['cookie']


def test_http_post_sends_json_body(http_server):
    response = http_post('{}/submit'.format(http_server), json={'key': 'value'})

    echoed = response.json()
    assert echoed['method'] == 'POST'
    assert json.loads(echoed['body']) == {'key': 'value'}
    assert echoed['headers']['content-type'] == 'application/json'


def test_http_post_sends_form_body(http_server):
    response = http_post('{}/submit'.format(http_server), data={'key': 'value'})

    echoed = response.json()
    assert 'key=value' in echoed['body']
    assert echoed['headers']['content-type'] == 'application/x-www-form-urlencoded'


def test_http_put_sends_body(http_server):
    response = http_put('{}/resource'.format(http_server), data='payload')

    echoed = response.json()
    assert echoed['method'] == 'PUT'
    assert echoed['body'] == 'payload'


def test_http_patch_sends_body(http_server):
    response = http_patch('{}/resource'.format(http_server), data='delta')

    echoed = response.json()
    assert echoed['method'] == 'PATCH'
    assert echoed['body'] == 'delta'


def test_http_delete_reaches_real_server(http_server):
    response = http_delete('{}/resource'.format(http_server))

    echoed = response.json()
    assert echoed['method'] == 'DELETE'
    assert echoed['path'] == '/resource'


def test_http_head_reaches_real_server(http_server):
    response = http_head(http_server)

    assert response.status_code == 200
    assert response.headers['X-Echo-Method'] == 'HEAD'


def test_raise_for_status_raises_agnostic_error(http_server):
    response = http_get('{}/status/404'.format(http_server))

    assert response.status_code == 404
    with pytest.raises(http_exceptions.HTTPStatusError):
        response.raise_for_status()


def test_http_get_follows_redirect(http_server):
    response = http_get('{}/redirect'.format(http_server))

    assert response.status_code == 200
    assert response.json()['path'] == '/final'


def test_http_get_server_error_status(http_server):
    response = http_get('{}/status/500'.format(http_server))

    assert response.status_code == 500
    with pytest.raises(http_exceptions.HTTPStatusError):
        response.raise_for_status()


def test_connection_failure_raises_agnostic_error(refused_url):
    # A refused connection maps requests.ConnectionError -> the specific HTTPConnectionError.
    with pytest.raises(http_exceptions.HTTPConnectionError):
        http_get(refused_url)


def test_dev_http_client_persist_flag():
    assert dev_http_client(persist=True).persist_connections is True
    assert dev_http_client().persist_connections is False


def test_dev_http_client_applies_default_options(http_server):
    client = dev_http_client(headers={'X-Default': 'yes'})

    response = client.get(http_server)

    assert response.json()['headers']['x-default'] == 'yes'


def test_dev_http_client_per_call_overrides_client_level(http_server):
    client = dev_http_client(headers={'X-Test': 'client'})

    response = client.get(http_server, headers={'X-Test': 'percall'})

    assert response.json()['headers']['x-test'] == 'percall'


def test_dev_http_client_verify_propagation():
    assert dev_http_client(verify=False).options['verify'] is False
    assert dev_http_client().options['verify']


def test_dev_http_client_reuses_connection_when_persistent(http_server):
    client = dev_http_client(persist=True)

    first = client.get('{}/one'.format(http_server))
    second = client.get('{}/two'.format(http_server))

    # A reused keep-alive connection keeps the same client source port across both calls.
    assert first.json()['client_port'] == second.json()['client_port']


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
