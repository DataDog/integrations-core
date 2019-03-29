# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.tls.utils import days_to_seconds

from .utils import download_cert, temp_binary


@pytest.fixture(scope='session', autouse=True)
def dd_environment():
    yield {'server': 'https://www.google.com'}


@pytest.fixture
def instance_local_no_cert():
    return {}


@pytest.fixture
def instance_local_no_server_hostname():
    return {'local_cert_path': 'cert.pem'}


@pytest.fixture
def instance_local_not_found():
    return {'local_cert_path': 'not_found.pem', 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_ok():
    with download_cert('ok.pem', 'https://www.google.com') as cert:
        yield {'local_cert_path': cert, 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_ok_der():
    with download_cert('ok.crt', 'https://www.google.com', raw=True) as cert:
        yield {'local_cert_path': cert, 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_hostname():
    instance = {'server_hostname': 'www.google.com'}

    with download_cert('ok.pem', instance['server_hostname']) as cert:
        instance['local_cert_path'] = cert

        yield instance


@pytest.fixture(scope='session')
def instance_local_hostname_mismatch():
    with download_cert('mismatch.pem', 'www.bing.com') as cert:
        yield {'local_cert_path': cert, 'server_hostname': 'www.google.com'}


@pytest.fixture(scope='session')
def instance_local_cert_bad():
    with temp_binary(b'junk') as f:
        yield {'local_cert_path': f, 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_cert_expired():
    with download_cert('expired.pem', 'https://expired.badssl.com') as cert:
        yield {'local_cert_path': cert, 'validate_hostname': False}


@pytest.fixture(scope='session')
def instance_local_cert_critical_days():
    with download_cert('critical.pem', 'https://www.google.com') as cert:
        yield {'local_cert_path': cert, 'validate_hostname': False, 'days_critical': 1000}


@pytest.fixture(scope='session')
def instance_local_cert_critical_seconds():
    with download_cert('critical.pem', 'https://www.google.com') as cert:
        yield {
            'local_cert_path': cert,
            'validate_hostname': False,
            'days_critical': -1,
            'seconds_critical': days_to_seconds(1000),
        }


@pytest.fixture(scope='session')
def instance_local_cert_warning_days():
    with download_cert('warning.pem', 'https://www.google.com') as cert:
        yield {'local_cert_path': cert, 'validate_hostname': False, 'days_warning': 1000}


@pytest.fixture(scope='session')
def instance_local_cert_warning_seconds():
    with download_cert('warning.pem', 'https://www.google.com') as cert:
        yield {
            'local_cert_path': cert,
            'validate_hostname': False,
            'days_warning': -1,
            'seconds_warning': days_to_seconds(1000),
        }


@pytest.fixture
def instance_remote_no_server():
    return {}


@pytest.fixture
def instance_remote_ok():
    return {'server': 'https://www.google.com'}


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
    return {'server': 'https://tls-v1-1.badssl.com:1011'}


@pytest.fixture
def instance_remote_version_default_1_2():
    return {'server': 'https://tls-v1-2.badssl.com:1012'}


@pytest.fixture
def instance_remote_version_default_1_3():
    return {'server': 'https://1.1.1.1'}


@pytest.fixture
def instance_remote_hostname_mismatch():
    return {'server': 'https://wrong.host.badssl.com'}


@pytest.fixture
def instance_remote_cert_expired():
    return {'server': 'https://expired.badssl.com'}


@pytest.fixture
def instance_remote_cert_critical_days():
    return {'server': 'https://www.google.com', 'days_critical': 1000}


@pytest.fixture
def instance_remote_cert_critical_seconds():
    return {'server': 'https://www.google.com', 'days_critical': -1, 'seconds_critical': days_to_seconds(1000)}


@pytest.fixture
def instance_remote_cert_warning_days():
    return {'server': 'https://www.google.com', 'days_warning': 1000}


@pytest.fixture
def instance_remote_cert_warning_seconds():
    return {'server': 'https://www.google.com', 'days_warning': -1, 'seconds_warning': days_to_seconds(1000)}
