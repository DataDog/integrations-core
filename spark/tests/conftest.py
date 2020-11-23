# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from datadog_test_libs.utils.mock_dns import mock_local

from datadog_checks.dev import docker_run

from .common import HERE, HOST, HOSTNAME_TO_PORT_MAPPING, INSTANCE_STANDALONE


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, 'docker', 'docker-compose.yaml'),
        build=True,
        endpoints=['http://{}:{}/api/v1/applications'.format(HOST, port) for port in (4040, 4050)],
        sleep=5,
    ):
        yield INSTANCE_STANDALONE


@pytest.fixture(scope='session', autouse=True)
def mock_local_tls_dns():
    with mock_local(HOSTNAME_TO_PORT_MAPPING):
        yield
