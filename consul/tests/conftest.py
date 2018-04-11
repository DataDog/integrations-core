# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import os
import time
import logging

import pytest
import mock
import requests

import common
import consul_mocks

log = logging.getLogger(__file__)


def wait_for_cluster():
    """
    Wait for the slave to connect to the master
    """
    connected = False
    for i in xrange(0, 20):
        try:
            requests.get(common.URL)
            return True
        except:
            log.info()
            pass

    return False


@pytest.fixture(scope="session")
def spin_up_consul():
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
