# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import subprocess
import stat
import os
import logging
import pytest
import time

import common

log = logging.getLogger(__file__)


def wait_on_docker_logs(container_name, max_wait, sentences):
    args = [
        'docker',
        'logs',
        container_name
    ]
    log.info("Waiting for {} to come up".format(container_name))
    for _ in range(max_wait):
        out = subprocess.check_output(args)
        if any(s in out for s in sentences):
            log.info('{} is up!'.format(container_name))
            return True
        time.sleep(1)

    log.info(out)
    return False


def get_container_ip(container_id_or_name):
    """
    Get a docker container's IP address from its id or name
    """
    args = [
        'docker', 'inspect',
        '-f', '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', container_id_or_name
    ]

    return subprocess.check_output(args).strip()


@pytest.fixture(scope="session")
def cassandra_cluster():
    """
        Start the cassandra cluster with required configuration
    """
    env = os.environ
    env['CONTAINER_PORT'] = common.PORT

    # We need to restrict permission on the password file
    os.chmod(os.path.join(common.HERE, 'compose', 'jmxremote.password'), stat.S_IRUSR)

    docker_compose_args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    ]
    subprocess.check_call(docker_compose_args + ["up", "-d", common.CASSANDRA_CONTAINER_NAME])

    # wait for the cluster to be up before yielding
    if not wait_on_docker_logs(
            common.CASSANDRA_CONTAINER_NAME,
            20,
            ['Listening for thrift clients', "Created default superuser role 'cassandra'"]
    ):
        raise Exception("Cassandra cluster dd-test-cassandra boot timed out!")

    cassandra_seed = get_container_ip("{}".format(common.CASSANDRA_CONTAINER_NAME))
    env['CASSANDRA_SEEDS'] = cassandra_seed
    subprocess.check_call(docker_compose_args + ["up", "-d", common.CASSANDRA_CONTAINER_NAME_2])

    if not wait_on_docker_logs(
            common.CASSANDRA_CONTAINER_NAME_2,
            50,
            ['Listening for thrift clients', 'Not starting RPC server as requested']
    ):
        raise Exception("Cassandra cluster {} boot timed out!".format(common.CASSANDRA_CONTAINER_NAME_2))

    subprocess.check_call([
        "docker",
        "exec", common.CASSANDRA_CONTAINER_NAME,
        "cqlsh",
        "-e", "CREATE KEYSPACE test WITH REPLICATION={'class':'SimpleStrategy', 'replication_factor':2}"
    ])
    yield

    subprocess.check_call(docker_compose_args + ["down"])


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator
