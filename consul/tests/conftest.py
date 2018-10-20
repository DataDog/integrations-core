# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests

from datadog_checks.dev import WaitFor, docker_run
from . import common


def _consul_config_path():
    server_file = 'server-{}.json'.format(os.getenv('CONSUL_VERSION'))
    return os.path.join(common.HERE, 'compose', server_file)


def ping_cluster():
    """
    Wait for the slave to connect to the master
    """
    response = requests.get('{}/v1/status/peers'.format(common.URL))
    response.raise_for_status()

    # Wait for all 3 agents to join the cluster
    if len(response.json()) == 3:
        return True

    return False


@pytest.fixture(scope='session')
def dd_environment(instance):
    """
    Start a cluster with one master, one replica, and one unhealthy replica.
    """
    env_vars = {
        'CONSUL_CONFIG_PATH': _consul_config_path(),
        'CONSUL_PORT': common.PORT,
    }

    with docker_run(
        os.path.join(common.HERE, 'compose', 'compose.yaml'),
        conditions=[WaitFor(ping_cluster)],
        env_vars=env_vars,
    ):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {
        'url': common.URL,
        'catalog_checks': True,
        'network_latency_checks': True,
        'new_leader_checks': True,
        'self_leader_check': True,
        'acl_token': 'token',
    }


@pytest.fixture(scope='session')
def instance_bad_token():
    return {
        'url': common.URL,
        'catalog_checks': True,
        'network_latency_checks': True,
        'new_leader_checks': True,
        'self_leader_check': True,
        'acl_token': 'wrong_token',
    }
