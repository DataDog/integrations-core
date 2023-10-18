# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import sys
import time
from copy import deepcopy

import pytest
from six import StringIO

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev import RetryError, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.zk import ZookeeperCheck
from datadog_checks.zk.zk import ZKConnectionFailure

CHECK_NAME = 'zk'
HOST = get_docker_hostname()
PORT = 12181
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)

VALID_CONFIG = {
    'host': HOST,
    'port': PORT,
    'expected_mode': "standalone",
    'tags': ["mytag"],
    'timeout': 500,
}

VALID_TLS_CONFIG = {
    'host': HOST,
    'port': PORT,
    'expected_mode': "standalone",
    'tags': ["mytag"],
    'timeout': 500,
    'use_tls': True,
    'tls_private_key': '/conf/private_key.pem',
    'tls_ca_cert': '/conf/ca_cert.pem',
    'tls_cert': '/conf/cert.pem',
    'tls_private_key_password': 'testpass',
}

# This is different than VALID_TLS_CONFIG since the key locations are different
VALID_TLS_CONFIG_FOR_TEST = {
    'host': HOST,
    'port': PORT,
    'expected_mode': "standalone",
    'tags': ["mytag"],
    'timeout': 500,
    'use_tls': True,
    'tls_private_key': os.path.join(HERE, 'compose/client', 'private_key.pem'),
    'tls_ca_cert': os.path.join(HERE, 'compose/client', 'ca_cert.pem'),
    'tls_cert': os.path.join(HERE, 'compose/client', 'cert.pem'),
    'tls_private_key_password': 'testpass',
}

STATUS_TYPES = ['leader', 'follower', 'observer', 'standalone', 'down', 'inactive', 'unknown']


@pytest.fixture(scope="session")
def get_instance():
    if get_tls():
        return VALID_TLS_CONFIG
    return VALID_CONFIG


@pytest.fixture(scope="session")
def get_test_instance():
    if get_tls():
        return VALID_TLS_CONFIG_FOR_TEST
    return VALID_CONFIG


@pytest.fixture
def get_invalid_mode_instance():
    invalid_mode = deepcopy(VALID_CONFIG)
    if get_tls():
        invalid_mode = deepcopy(VALID_TLS_CONFIG_FOR_TEST)

    invalid_mode['expected_mode'] = "follower"
    return invalid_mode


@pytest.fixture
def get_conn_failure_config():
    conn_failure_config = deepcopy(VALID_CONFIG)
    if get_tls():
        conn_failure_config = deepcopy(VALID_TLS_CONFIG_FOR_TEST)
    conn_failure_config['port'] = 2182
    conn_failure_config['expected_mode'] = 'down'
    conn_failure_config['tags'] = ["mytag"]
    return conn_failure_config


@pytest.fixture
def get_multiple_expected_modes_config():
    config = deepcopy(VALID_CONFIG)
    config.update({'expected_mode': ['standalone', 'leader']})
    return config


def get_version():
    zk_version = os.environ.get("ZK_VERSION")
    version = [int(k) for k in zk_version.split(".")]
    if len(version) == 2:
        version += [0]
    return version


def get_tls():
    return os.environ.get("SSL") == 'True'


@pytest.fixture(scope="session")
def dd_environment(get_instance):
    def condition_non_tls():
        sys.stderr.write("Waiting for ZK to boot...\n")
        booted = False
        dummy_instance = {'host': HOST, 'port': PORT, 'timeout': 500}
        for _ in range(10):
            try:
                out = ZookeeperCheck('zk', {}, [dummy_instance])._send_command('ruok')
                out.seek(0)
                if out.readline() != 'imok':
                    raise ZKConnectionFailure()
                booted = True
                break
            except ZKConnectionFailure:
                time.sleep(1)

        if not booted:
            raise RetryError("Zookeeper failed to boot!")
        sys.stderr.write("ZK boot complete.\n")

    is_tls = get_tls()
    compose_file = os.path.join(HERE, 'compose', 'zk.yaml')
    if [3, 5, 0] <= get_version() < [3, 6, 0]:
        compose_file = os.path.join(HERE, 'compose', 'zk35.yaml')
        if is_tls:
            compose_file = os.path.join(HERE, 'compose', 'zk35_ssl.yaml')
    elif get_version() >= [3, 6, 0]:
        compose_file = os.path.join(HERE, 'compose', 'zk36plus.yaml')
        if is_tls:
            compose_file = os.path.join(HERE, 'compose', 'zk36plus_ssl.yaml')

    private_key = os.path.join(HERE, 'compose/client', 'private_key.pem')
    cert = os.path.join(HERE, 'compose/client', 'cert.pem')
    ca_cert = os.path.join(HERE, 'compose/client', 'ca_cert.pem')

    if is_tls:
        condition = [
            CheckDockerLogs(compose_file, patterns=['Starting server', 'Started AdminServer', 'bound to port'])
        ]
    else:
        condition = [condition_non_tls]

    with docker_run(compose_file, conditions=condition, sleep=5):
        yield get_instance, {
            'docker_volumes': [
                '{}:/conf/private_key.pem'.format(private_key),
                '{}:/conf/cert.pem'.format(cert),
                '{}:/conf/ca_cert.pem'.format(ca_cert),
            ]
        }


@pytest.fixture()
def mock_mntr_output():
    buffer = StringIO()
    f_name = os.path.join(HERE, 'fixtures', 'mntr_metrics')
    with open(f_name) as f:
        data = f.read()
        buffer.write(data)

    yield buffer
