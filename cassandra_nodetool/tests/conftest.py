# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.docker import get_container_ip, run_in_container

from . import common

E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y docker.io',
    ],
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock'],
}


@pytest.fixture(scope="session")
def dd_environment():
    """Start the cassandra cluster with required configuration."""
    env = os.environ
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    env['CONTAINER_PORT'] = common.PORT

    with docker_run(
        compose_file,
        service_name=common.CASSANDRA_CONTAINER_NAME,
        log_patterns=['Listening for thrift clients'],
        build=True,
    ):
        cassandra_seed = get_container_ip("{}".format(common.CASSANDRA_CONTAINER_NAME))
        env['CASSANDRA_SEEDS'] = cassandra_seed
        with docker_run(
            compose_file,
            service_name=common.CASSANDRA_CONTAINER_NAME_2,
            log_patterns=['All sessions completed', 'Starting listening for CQL clients'],
        ):
            command = [
                "cqlsh",
                "-e",
                "\"CREATE KEYSPACE IF NOT EXISTS test WITH REPLICATION"
                "={'class':'SimpleStrategy', 'replication_factor':2}\"",
            ]
            run_in_container(common.CASSANDRA_CONTAINER_NAME, command)
            yield common.CONFIG_INSTANCE, E2E_METADATA
