# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import os
import logging

import pytest
import requests

import common

log = logging.getLogger(__file__)


def wait_for_cluster():
    """
    Wait for the slave to connect to the master
    """
    from time import sleep
    for i in xrange(0, 50):
        sleep(1)
        try:
            res = requests.get("{}/v1/status/peers".format(common.URL))
            # Wait for all 3 agents to join the cluster
            if len(res.json()) == 3:
                return True
        except Exception as e:
            log.info("Error connecting to the cluster: %s", e)
            pass

    return False


@pytest.fixture(scope="session")
def consul_cluster():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    env = os.environ
    env['CONSUL_CONFIG_PATH'] = _consul_config_path()
    env['CONSUL_PORT'] = common.PORT

    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'compose.yaml')
    ]

    subprocess.check_call(args + ["down"])
    subprocess.check_call(args + ["up", "-d"])
    # wait for the cluster to be up before yielding
    if not wait_for_cluster():
        raise Exception("Consul cluster boot timed out!")
    yield
    subprocess.check_call(args + ["down"])


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def _consul_config_path():
    server_file = "server-{0}.json".format(_consul_version())
    return os.path.join(common.HERE, 'compose', server_file)


def _consul_version():
    return os.getenv("CONSUL_VERSION")
