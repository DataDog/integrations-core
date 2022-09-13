# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here


TEST_SERVER_ADDRESS = '{}:8080'.format(get_docker_hostname())
READY_ENDPOINT = 'http://{}:8081/ready'.format(get_docker_hostname())
INSTANCE = {'addr': TEST_SERVER_ADDRESS}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'docker', 'docker-compose.yml')

    # This does 3 things:
    #
    # 1. Spins up the services defined in the compose file
    # 2. Waits for the url to be available before running the tests
    # 3. Tears down the services when the tests are finished
    print(READY_ENDPOINT)
    with docker_run(compose_file,
            build=True,
            endpoints=[READY_ENDPOINT],
            attempts=2):
        yield INSTANCE


@pytest.fixture
def instance():
    return INSTANCE.copy()
