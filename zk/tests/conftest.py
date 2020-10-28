# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import sys
import time

import pytest

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev import RetryError, docker_run
from datadog_checks.zk import ZookeeperCheck
from datadog_checks.zk.zk import ZKConnectionFailure

CHECK_NAME = 'zk'
HOST = get_docker_hostname()
PORT = 12181
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)

VALID_CONFIG = {'host': HOST, 'port': PORT, 'expected_mode': "standalone", 'tags': ["mytag"]}

VALID_SSL_CONFIG = {
    'host': HOST,
    'port': PORT,
    'expected_mode': "standalone",
    'tags': ["mytag"],
    'timeout': 500,
    'ssl': True,
    'private_key': '/conf/private_key.pem',
    'ca_cert': '/conf/ca_cert.pem',
    'cert': '/conf/cert.pem',
    'password': 'testpass',
}

STATUS_TYPES = ['leader', 'follower', 'observer', 'standalone', 'down', 'inactive', 'unknown']


@pytest.fixture(scope="session")
def get_instance():
    if get_ssl():
        return VALID_SSL_CONFIG
    return VALID_CONFIG


@pytest.fixture
def get_invalid_mode_instance():
    return {'host': HOST, 'port': PORT, 'expected_mode': "follower", 'tags': []}


@pytest.fixture
def get_conn_failure_config():
    return {'host': HOST, 'port': 2182, 'expected_mode': "down", 'tags': []}


def get_version():
    zk_version = os.environ.get("ZK_VERSION")
    version = [int(k) for k in zk_version.split(".")]
    if len(version) == 2:
        version += [0]
    return version


def get_ssl():
    return os.environ.get("SSL") == 'True'


@pytest.fixture(scope="session")
def dd_environment(get_instance):
    def condition():
        sys.stderr.write("Waiting for ZK to boot...\n")
        booted = False
        # TODO: This doesn't work for SSL yet
        dummy_instance = {
            'host': HOST,
            'port': PORT,
            'timeout': 500,
            'ssl': get_ssl(),
            'private_key': os.path.join(HERE, 'compose', 'private_key.pem'),
            'ca_cert': os.path.join(HERE, 'compose', 'ca_cert.pem'),
            'cert': os.path.join(HERE, 'compose', 'cert.pem'),
            'password': 'testpass',
        }
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

    compose_file = os.path.join(HERE, 'compose', 'zk.yaml')
    if [3, 5, 0] <= get_version() < [3, 6, 0]:
        compose_file = os.path.join(HERE, 'compose', 'zk35.yaml')
    elif get_version() >= [3, 6, 0]:
        compose_file = os.path.join(HERE, 'compose', 'zk36plus.yaml')

    if get_ssl():
        compose_file = os.path.join(HERE, 'compose', 'zk36plus_ssl.yaml')

    private_key = os.path.join(HERE, 'compose', 'private_key.pem')
    cert = os.path.join(HERE, 'compose', 'cert.pem')
    ca_cert = os.path.join(HERE, 'compose', 'ca_cert.pem')

    with docker_run(compose_file, conditions=[condition]):
        yield get_instance, {
            'docker_volumes': [
                '{}:/conf/private_key.pem'.format(private_key),
                '{}:/conf/cert.pem'.format(cert),
                '{}:/conf/ca_cert.pem'.format(ca_cert),
            ]
        }

