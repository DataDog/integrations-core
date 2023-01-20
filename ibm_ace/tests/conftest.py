# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


@pytest.fixture(scope='session')
def dd_environment(instance_no_subscriptions):
    with docker_run(
        common.COMPOSE_FILE,
        build=True,
        conditions=[
            CheckDockerLogs(
                common.COMPOSE_FILE,
                ['Integration server is ready', 'Started web server'],
                matches='all',
                attempts=35,
                wait=2,
            ),
        ],
        env_vars={
            'IBM_ACE_IMAGE': common.DOCKER_IMAGE_VERSIONS[os.environ['IBM_ACE_VERSION']],
            'ACE_SERVER_NAME': common.ACE_SERVER_NAME,
        },
        attempts=3,
    ):
        yield instance_no_subscriptions, common.E2E_METADATA


@pytest.fixture(scope='session')
def instance_no_subscriptions(instance):
    # Make the live Agent do nothing by default so tests collect everything
    return {'resource_statistics': False, 'message_flows': False, **instance}


@pytest.fixture(scope='session')
def instance():
    return {
        'mq_server': common.SERVER,
        'mq_port': 11414,
        'channel': 'DEV.ADMIN.SVRCONN',
        'queue_manager': 'QM1',
        'mq_user': 'admin',
        'mq_password': 'passw0rd',
        'tags': ['foo:bar'],
    }


@pytest.fixture(scope='session')
def global_tags(instance):
    return [f'mq_server:{instance["mq_server"]}', f'mq_port:{instance["mq_port"]}', *instance['tags']]
