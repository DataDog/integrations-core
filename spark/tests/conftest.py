# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run

from .common import HERE, HOST, INSTANCE_STANDALONE


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, 'docker', 'docker-compose.yaml'),
        build=True,
        endpoints='http://{}:4040/api/v1/applications'.format(HOST),
        sleep=5,
    ):
        yield INSTANCE_STANDALONE
