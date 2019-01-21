# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from .common import HERE, HOST


@pytest.fixture(scope='session')
def dd_environment(instance_standalone):
    with docker_run(
        compose_file=os.path.join(HERE, 'docker', 'docker-compose.yaml'),
        endpoints='http://{}:4040/api/v1/applications'.format(HOST),
        sleep=5,
    ):
        yield instance_standalone


@pytest.fixture(scope='session')
def instance_standalone():
    return {
        'spark_url': 'http://{}:8080'.format(HOST),
        'cluster_name': 'SparkCluster',
        'spark_cluster_mode': 'spark_standalone_mode'
    }
