# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import ssl
import subprocess
import tempfile
import threading
from xmlrpc.server import SimpleXMLRPCServer

import mock
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.http import MockResponse
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


def mock_requests_get(url, *args, **kwargs):
    url_parts = url.split('/')
    print(url_parts)

    if url_parts[0] == 'wrong':
        return MockResponse(status_code=404)

    json_file = f"rrd_updates_{url_parts[0]}.json" if url_parts[1] == "rrd_updates" else f"{url_parts[1]}.json"
    path = os.path.join(common.HERE, 'fixtures', 'standalone', json_file)
    if not os.path.exists(path):
        return MockResponse(status_code=404)

    return MockResponse(file_path=path)


@pytest.fixture
def mock_responses():
    with mock.patch('requests.Session.get', side_effect=mock_requests_get):
        yield


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
