# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests

from datadog_checks.dev import docker_run
from .common import HERE, MAIN_URL


@pytest.fixture(scope='session', autouse=True)
def spin_up_etcd():
    compose_file = os.path.join(HERE, 'docker', 'docker-compose.yaml')

    with docker_run(
        compose_file,
        endpoints=(
            '{}/v2/stats/self'.format(MAIN_URL),
            '{}/v2/stats/store'.format(MAIN_URL),
        )
    ):
        requests.post('{}/v2/keys/message'.format(MAIN_URL), data={'value': 'Hello world'})
        yield compose_file


@pytest.fixture
def main_instance():
    return {
        'url': MAIN_URL,
    }
