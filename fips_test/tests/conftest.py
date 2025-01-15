# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run

HERE = os.path.dirname(os.path.abspath(__file__))

CA_CERT = os.path.join(HERE, 'compose', 'ca.crt')
CA_CERT_MOUNT_PATH = '/tmp/ca.crt'


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(os.path.join(HERE, 'compose', 'docker-compose.yml'), build=True, sleep=20):
        e2e_metadata = {'docker_volumes': ['{}:{}'.format(CA_CERT, CA_CERT_MOUNT_PATH)]}
        yield instance_e2e_fips, instance_e2e_non_fips, e2e_metadata


@pytest.fixture(scope='session')
def instance_e2e_fips():
    return {
        'server': 'https://localhost',
        'port': 8443,
        'tls_ca_cert': CA_CERT_MOUNT_PATH,
        'tls_verify': False,
        'tls_validate_hostname': False,
    }


@pytest.fixture(scope='session')
def instance_e2e_non_fips():
    return {
        'server': 'https://localhost',
        'port': 9443,
        'tls_ca_cert': CA_CERT_MOUNT_PATH,
        'tls_verify': False,
        'tls_validate_hostname': False,
    }
