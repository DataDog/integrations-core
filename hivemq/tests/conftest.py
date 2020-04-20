# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.utils import load_jmx_config

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'docker', 'docker-compose.yaml')
    with docker_run(
        compose_file,
        mount_logs=True,
        conditions=[CheckDockerLogs(compose_file, ['Started HiveMQ in'], matches='all')],
    ):
        config = load_jmx_config()
        config['instances'] = [common.INSTANCE]
        yield config, {'use_jmx': True}
