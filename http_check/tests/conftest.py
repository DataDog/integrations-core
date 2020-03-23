# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import pytest
from mock import patch

from datadog_checks.dev import docker_run, run_command
from datadog_checks.dev.utils import ON_WINDOWS

from .common import CONFIG_E2E, HERE

MOCKED_HOSTS = ['valid.mock', 'expired.mock', 'wronghost.mock', 'selfsigned.mock']


@pytest.fixture(scope='session')
def dd_environment():
    cacert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    e2e_metadata = {'docker_volumes': ['{}:/opt/cacert.pem'.format(cacert_path)]}
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yml'), build=True, log_patterns=["starting server on port"]
    ):
        yield CONFIG_E2E, e2e_metadata


@pytest.fixture(scope='session')
def mock_dns():
    import socket

    _orig_getaddrinfo = socket.getaddrinfo
    _orig_connect = socket.socket.connect

    def patched_getaddrinfo(host, *args, **kwargs):
        if host.endswith('.mock'):
            # See socket.getaddrinfo, just updating the hostname here.
            # https://docs.python.org/3/library/socket.html#socket.getaddrinfo
            return [(2, 1, 6, '', ('127.0.0.1', 443))]

        return _orig_getaddrinfo(host, *args, **kwargs)

    def patched_connect(self, address):
        host, port = address[0], address[1]
        if host.endswith('.mock'):
            host, port = '127.0.0.1', 443

        return _orig_connect(self, (host, port))

    socket.getaddrinfo = patched_getaddrinfo
    socket.socket.connect = patched_connect
    yield
    socket.getaddrinfo = _orig_getaddrinfo
    socket.socket.connect = _orig_connect


@pytest.fixture()
def mock_hosts_e2e():
    """Only for e2e testing"""
    container_id = "dd_http_check_{}".format(os.environ["TOX_ENV_NAME"])
    commands = []
    for mocked_host in MOCKED_HOSTS:
        commands.append(r'bash -c "printf \"127.0.0.1 {}\n\" >> /etc/hosts"'.format(mocked_host))

    for command in commands:
        run_command('docker exec {} {}'.format(container_id, command))


@pytest.fixture(scope='session')
def http_check():
    from datadog_checks.http_check import HTTPCheck

    # Patch the function to return the certs located in the `tests/` folder
    with patch('datadog_checks.http_check.http_check.get_ca_certs_path', new=mock_get_ca_certs_path):
        yield HTTPCheck('http_check', {}, [{}])


@pytest.fixture(scope='session')
def embedded_dir():
    if ON_WINDOWS:
        return 'embedded{}'.format(sys.version_info[0])
    else:
        return 'embedded'


def mock_get_ca_certs_path():
    """
    Mimic get_ca_certs_path() by using the certificates located in the `tests/` folder
    """
    embedded_certs = os.path.join(HERE, 'fixtures', 'cacert.pem')

    if os.path.exists(embedded_certs):
        return embedded_certs

    raise Exception("Embedded certs not found: {}".format(embedded_certs))
