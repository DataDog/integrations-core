# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from packaging.version import parse as parse_version

from datadog_checks.base import is_affirmative
from datadog_checks.dev import docker_run, run_command

from .common import COCKROACHDB_VERSION, HERE, HOST, PORT


@pytest.fixture(scope='session')
def dd_environment(instance):
    env_vars = {'COCKROACHDB_START_COMMAND': _get_start_command()}

    conditions = [run_sql] if is_affirmative(os.environ.get("POPULATE_METRICS")) else None

    with docker_run(
        os.path.join(HERE, 'docker', 'docker-compose.yaml'),
        env_vars=env_vars,
        endpoints=instance['openmetrics_endpoint'],
        conditions=conditions,
    ):
        yield instance


@pytest.fixture(scope='session')
def instance_legacy():
    return {'prometheus_url': 'http://{}:{}/_status/vars'.format(HOST, PORT)}


@pytest.fixture(scope='session')
def instance():
    return {
        'openmetrics_endpoint': 'http://{}:{}/_status/vars'.format(HOST, PORT),
        'histogram_buckets_as_distributions': True,
        'tags': ['cluster:cockroachdb-cluster', 'node:1'],
    }


def _get_start_command():
    if COCKROACHDB_VERSION != 'latest' and parse_version(COCKROACHDB_VERSION) < parse_version('20.2'):
        return 'start'
    return 'start-single-node'


def run_sql():
    return run_command(['docker', 'exec', '-d', 'cockroachdb', '/bin/bash', '/sql.sh'], capture=True, check=True)
