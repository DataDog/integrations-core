# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from six import iteritems

from datadog_checks.dev import TempDir, docker_run
from datadog_checks.tls.utils import days_to_seconds

from .utils import download_cert, temp_binary

HERE = os.path.dirname(os.path.abspath(__file__))

CA_CERT = os.path.join(HERE, 'compose', 'ca.crt')

HOSTNAME_TO_PORT_MAPPING = {
    "tls-v1-1.valid.mock": 4444,
    "tls-v1-2.valid.mock": 4445,
    "tls-v1-3.valid.mock": 4446,
}


@pytest.fixture(scope='session', autouse=True)
def dd_environment(instance_e2e):
    with docker_run(os.path.join(HERE, 'compose', 'docker-compose.yml'), build=True, sleep=5):
        e2e_metadata = {'docker_volumes': ['{}:{}'.format(CA_CERT, CA_CERT)]}
        yield instance_e2e, e2e_metadata


@pytest.fixture(scope='session', autouse=True)
def mock_dns():
    import socket

    _orig_getaddrinfo = socket.getaddrinfo

    def patched_getaddrinfo(host, *args, **kwargs):
        if host.endswith('.mock'):
            # nginx doesn't support multiple tls versions from the same container
            port = HOSTNAME_TO_PORT_MAPPING.get(host, 4443)

            # See socket.getaddrinfo, just updating the hostname here.
            # https://docs.python.org/3/library/socket.html#socket.getaddrinfo
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
    with TempDir('certs') as tmp_dir:
        for address, name in iteritems(downloads):
            filepath = os.path.join(tmp_dir, name)
            download_cert(filepath, address)
            certs[name] = filepath
        for address, name in iteritems(raw_downloads):
            filepath = os.path.join(tmp_dir, name)
            certs[name] = download_cert(filepath, address, raw=True)
            certs[name] = filepath
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


@pytest.fixture(scope='session')
def instance_e2e():
    return {'server': 'https://localhost', 'port': 4443, 'server_hostname': 'valid.mock', 'ca_cert': CA_CERT}


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
