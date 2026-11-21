# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import ssl
import subprocess
import tempfile
import threading
from xmlrpc.server import SimpleXMLRPCServer

import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.dev import docker_run
from datadog_checks.dev.utils import find_free_port

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        common.COMPOSE_FILE,
        endpoints=[
            '{}/rrd_updates'.format(common.E2E_INSTANCE[0]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[1]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[2]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[3]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[4]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[5]['url']),
        ],
    ):
        yield common.E2E_INSTANCE


@pytest.fixture(params=common.MOCKED_INSTANCES, ids=common.MOCKED_INSTANCE_IDS)
def instance(request):
    return request.param


# The fake matches exact URLs, so every base URL a unit test configures is registered up front.
MOCKED_BASE_URLS = [*common.MOCKED_INSTANCE_IDS, 'mocked', 'wrong']


def fixture_response(base_url, endpoint):
    if base_url == 'wrong':
        return FakeHTTPResponse(status_code=404)

    json_file = f"rrd_updates_{base_url}.json" if endpoint == "rrd_updates" else f"{endpoint}.json"
    path = os.path.join(common.HERE, 'fixtures', 'standalone', json_file)
    if not os.path.exists(path):
        return FakeHTTPResponse(status_code=404)

    with open(path, 'rb') as f:
        content = f.read()

    # The fake does not parse its body, so mirror what a real response's json() returns or raises for this payload.
    try:
        return FakeHTTPResponse(content=content, json_result=json.loads(content))
    except json.JSONDecodeError as e:
        return FakeHTTPResponse(content=content, json_error=e)


@pytest.fixture
def mock_responses(fake_http):
    for base_url in MOCKED_BASE_URLS:
        for endpoint in ('host_rrd', 'rrd_updates'):
            fake_http.register_response('GET', f'{base_url}/{endpoint}', fixture_response(base_url, endpoint))


@pytest.fixture
def tls_xenserver():
    """Real HTTPS XML-RPC server backed by a fresh self-signed cert, for TLS behavior tests."""
    cert_file = tempfile.NamedTemporaryFile(delete=False, suffix='.crt')
    key_file = tempfile.NamedTemporaryFile(delete=False, suffix='.key')
    cert_file.close()
    key_file.close()
    subprocess.run(
        [
            'openssl',
            'req',
            '-x509',
            '-newkey',
            'rsa:2048',
            '-keyout',
            key_file.name,
            '-out',
            cert_file.name,
            '-days',
            '1',
            '-nodes',
            '-subj',
            '/CN=localhost',
        ],
        check=True,
    )

    port = find_free_port('127.0.0.1')
    server = SimpleXMLRPCServer(('127.0.0.1', port), logRequests=False)
    server.register_function(lambda username, password: common.SESSION_MASTER, 'session.login_with_password')

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file.name, keyfile=key_file.name)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield 'https://localhost:{}'.format(port)

    server.shutdown()
    server.server_close()
    thread.join()
    os.unlink(cert_file.name)
    os.unlink(key_file.name)
