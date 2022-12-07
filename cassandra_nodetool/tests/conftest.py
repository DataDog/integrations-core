# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.docker import get_container_ip

from . import common

E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y docker.io',
    ],
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock'],
    'env_vars': {'DD_IGNORE_AUTOCONF': 'docker'},
}


@pytest.fixture(scope="session")
def dd_environment():
    """Start the cassandra cluster with required configuration."""
    env = os.environ
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    env['CONTAINER_PORT'] = common.PORT
    env['CASSANDRA_SEEDS'] = '0.0.0.0'
    cassandra_version = int(env['CASSANDRA_VERSION'].split('.')[0])
    if cassandra_version >= 3:
        log_patterns = ['Starting listening for CQL clients', 'Startup complete']
    else:
        log_patterns = ['Starting listening for CQL clients', 'All sessions completed']

    with docker_run(
        compose_file,
        service_name=common.CASSANDRA_CONTAINER_NAME,
        log_patterns=['Listening for thrift clients'],
    ):
        cassandra_seed = get_container_ip("{}".format(common.CASSANDRA_CONTAINER_NAME))
        env['CASSANDRA_SEEDS'] = cassandra_seed
        with docker_run(
            compose_file,
            service_name=common.CASSANDRA_CONTAINER_NAME_2,
            conditions=[CheckDockerLogs(compose_file, log_patterns, matches='all', wait=2)],
        ):
            subprocess.check_call(
                [
                    "docker",
                    "exec",
                    common.CASSANDRA_CONTAINER_NAME,
                    "cqlsh",
                    "-e",
                    "CREATE KEYSPACE IF NOT EXISTS test \
                WITH REPLICATION={'class':'SimpleStrategy', 'replication_factor':2}",
                    "--request-timeout",
                    "20",
                ]
            )
            yield common.CONFIG_INSTANCE, E2E_METADATA
