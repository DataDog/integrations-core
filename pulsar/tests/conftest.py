# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.pulsar import PulsarCheck

from . import common


@pytest.fixture(scope='session')
def dd_environment(instance):
    env_vars = {'PULSAR_VERSION': common.PULSAR_VERSION}
    with docker_run(
        os.path.join(common.HERE, 'docker', 'docker-compose.yaml'),
        env_vars=env_vars,
        endpoints=instance['openmetrics_endpoint'],
        mount_logs=True,
        sleep=10,
    ):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {'openmetrics_endpoint': common.METRICS_URL}


@pytest.fixture(scope='session')
def pulsar_check():
    return lambda instance: PulsarCheck('pulsar', {}, [instance])
