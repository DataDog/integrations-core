# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import subprocess
import os
import logging
import pytest
import time

import common

log = logging.getLogger(__file__)


def wait_on_docker_logs(container_name, max_wait, sentences):
    count = 0
    args = [
        'docker',
        'logs',
        container_name
    ]
    out = subprocess.check_output(args)
    log.info("Waiting for {} to come up".format(container_name))
    if sentences is not None:
        while count < max_wait and not any(s in out for s in sentences):
            time.sleep(1)
            out = subprocess.check_output(args)
            count += 1

        if any(s in out for s in sentences):
            log.info(" {} is up!".format(container_name))
            return True
        else:
            print(out)
            log.info(out)
            return False

    return False


def get_container_ip(container_id_or_name):
    """
    Get a docker container's IP address from its id or name
    """
    args = [
        'docker', 'inspect',
        '-f', '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', container_id_or_name
    ]

    return subprocess.check_output(args).rstrip('\r\n')


@pytest.fixture(scope="session")
def cassandra_cluster():
    """
        Start the cassandra cluster with required configuration
    """
    env = os.environ
    env['CONTAINER_PORT'] = common.PORT

    # We need to restrict permission on the password file
    subprocess.check_call([
        "chmod",
        "400",
        os.path.join(common.HERE, 'compose', 'jmxremote.password')
    ])

    docker_compose_args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    ]
    subprocess.check_call(docker_compose_args + ["down"])

    subprocess.check_call(docker_compose_args + ["up", "-d", "dd-test-cassandra"])

    # wait for the cluster to be up before yielding
    if not wait_on_docker_logs("dd-test-cassandra", 20, ['Listening for thrift clients',
                                                         "Created default superuser role 'cassandra'"]):
        raise Exception("Cassandra cluster dd-test-cassandra boot timed out!")

    cassandra_seed = get_container_ip("dd-test-cassandra")
    env['CASSANDRA_SEEDS'] = cassandra_seed
    subprocess.check_call(docker_compose_args + ["up", "-d", "dd-test-cassandra2"])

    if not wait_on_docker_logs("dd-test-cassandra2", 50, ['Listening for thrift clients',
                               'Not starting RPC server as requested']):
        raise Exception("Cassandra cluster dd-test-cassandra2 boot timed out!")

    subprocess.check_call([
        "docker",
        "exec", "dd-test-cassandra",
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
