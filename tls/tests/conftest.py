# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from six import iteritems

from datadog_checks.dev import TempDir, docker_run
from datadog_checks.tls.utils import days_to_seconds

from .utils import download_cert, temp_binary

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


HERE = os.path.dirname(os.path.abspath(__file__))

CA_CERT = os.path.join(HERE, 'compose', 'ca.crt')


@pytest.fixture(scope='session', autouse=True)
def dd_environment():
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yml'), build=True,
    ):
        yield {'server': 'valid.mock'}


@pytest.fixture(scope='session', autouse=True)
def mock_dns():
    import socket

    _orig_getaddrinfo = socket.getaddrinfo

    def patched_getaddrinfo(host, *args, **kwargs):
        if host.endswith('.mock'):
            # nginx doesn't support multiple tls versions from the same container
            if 'tls-v1-1' in host:
                port = 4444
            elif 'tls-v1-2' in host:
                port = 4445
            elif 'tls-v1-3' in host:
                port = 4446
            else:
                port = 4443

            # See socket.getaddrinfo, just updating the hostname here.
            return [(2, 1, 6, '', ('127.0.0.1', port))]

        return _orig_getaddrinfo(host, *args, **kwargs)

    socket.getaddrinfo = patched_getaddrinfo
    yield
    socket.getaddrinfo = _orig_getaddrinfo


@pytest.fixture(scope='session', autouse=True)
def certs(dd_environment, mock_dns):
    downloads = {'https://valid.mock': 'valid.pem', 'https://expired.mock': 'expired.pem'}
    raw_downloads = {
        'https://valid.mock': 'valid.crt',
    }
    certs = {}
    with ExitStack() as stack:
        tmp_dir = stack.enter_context(TempDir())
        for address, name in iteritems(downloads):
            filepath = os.path.join(tmp_dir, name)
            certs[name] = stack.enter_context(download_cert(filepath, address))
        for address, name in iteritems(raw_downloads):
            filepath = os.path.join(tmp_dir, name)
            certs[name] = stack.enter_context(download_cert(filepath, address, raw=True))
        yield certs


@pytest.fixture
def instance_local_no_server_hostname():
    return {'local_cert_path': 'cert.pem'}


@pytest.fixture
def instance_local_not_found():
    return {'local_cert_path': 'not_found.pem', 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_ok(certs):
    yield {'local_cert_path': certs['valid.pem'], 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_ok_der(certs):
    yield {'local_cert_path': certs['valid.crt'], 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_hostname(certs):
    instance = {'server_hostname': 'valid.mock', 'local_cert_path': certs['valid.pem']}
    yield instance


@pytest.fixture(scope='session')
def instance_local_hostname_mismatch(certs):
    yield {'local_cert_path': certs['valid.pem'], 'server_hostname': 'wrong.host'}


@pytest.fixture(scope='session')
def instance_local_cert_bad():
    with temp_binary(b'junk') as f:
        yield {'local_cert_path': f, 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_cert_expired(certs):
    yield {'local_cert_path': certs['expired.pem'], 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_cert_critical_days(certs):
    yield {'local_cert_path': certs['valid.pem'], 'validate_hostname': False, 'days_critical': 200}


@pytest.fixture(scope='session')
def instance_local_cert_critical_seconds(certs):
    yield {
        'local_cert_path': certs['valid.pem'],
        'validate_hostname': False,
        'days_critical': -1,
        'seconds_critical': days_to_seconds(200),
    }


@pytest.fixture(scope='session')
def instance_local_cert_warning_days(certs):
    yield {'local_cert_path': certs['valid.pem'], 'validate_hostname': False, 'days_warning': 200}


@pytest.fixture(scope='session')
def instance_local_cert_warning_seconds(certs):
    yield {
        'local_cert_path': certs['valid.pem'],
        'validate_hostname': False,
        'days_warning': -1,
        'seconds_warning': days_to_seconds(200),
    }


@pytest.fixture
def instance_remote_no_server():
    return {}


@pytest.fixture
def instance_remote_ok():
    return {'server': 'https://valid.mock', 'ca_cert': CA_CERT}


@pytest.fixture
def instance_remote_ok_ip():
    return {'server': '1.1.1.1'}


@pytest.fixture
def instance_remote_ok_udp():
    return {'server': '1.1.1.1', 'transport': 'udp'}


@pytest.fixture
def instance_remote_no_resolve():
    return {'server': 'https://this.does.not.exist.foo'}


@pytest.fixture
def instance_remote_no_connect():
    return {'server': 'localhost', 'port': 56789}


@pytest.fixture
def instance_remote_no_connect_port_in_host():
    return {'server': 'localhost:56789'}


@pytest.fixture
def instance_remote_version_default_1_1():
    return {'server': 'https://tls-v1-1.valid.mock', 'ca_cert': CA_CERT}


@pytest.fixture
def instance_remote_version_default_1_2():
    return {'server': 'https://tls-v1-2.valid.mock', 'ca_cert': CA_CERT}


@pytest.fixture
def instance_remote_version_default_1_3():
    return {'server': 'https://tls-v1-3.valid.mock', 'ca_cert': CA_CERT}


@pytest.fixture
def instance_remote_hostname_mismatch():
    return {'server': 'https://wronghost.mock', 'ca_cert': CA_CERT}


@pytest.fixture
def instance_remote_self_signed_ok():
    return {'server': 'https://selfsigned.mock', 'validate_cert': False}


@pytest.fixture
def instance_remote_cert_expired():
    return {'server': 'https://expired.mock', 'ca_cert': CA_CERT}


@pytest.fixture
def instance_remote_cert_critical_days():
    return {'server': 'https://valid.mock', 'days_critical': 200, 'ca_cert': CA_CERT}


@pytest.fixture
def instance_remote_cert_critical_seconds():
    return {
        'server': 'https://valid.mock',
        'days_critical': -1,
        'seconds_critical': days_to_seconds(200),
        'ca_cert': CA_CERT,
    }


@pytest.fixture
def instance_remote_cert_warning_days():
    return {'server': 'https://valid.mock', 'days_warning': 200, 'ca_cert': CA_CERT}


@pytest.fixture
def instance_remote_cert_warning_seconds():
    return {
        'server': 'https://valid.mock',
        'days_warning': -1,
        'seconds_warning': days_to_seconds(200),
        'ca_cert': CA_CERT,
    }
