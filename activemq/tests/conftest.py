# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import time

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import WaitForPortListening
from datadog_checks.dev.utils import load_jmx_config

from .common import BASE_URL, HERE, HOST, JMX_PORT, TEST_AUTH, TEST_MESSAGE, TEST_PORT, TEST_QUEUES, TEST_TOPICS


def populate_server():
    """Add some queues and topics to ensure more metrics are available."""
    time.sleep(3)

    for queue in TEST_QUEUES:
        url = '{}/{}?type=queue'.format(BASE_URL, queue)
        requests.post(url, data=TEST_MESSAGE, auth=TEST_AUTH)

    for topic in TEST_TOPICS:
        url = '{}/{}?type=topic'.format(BASE_URL, topic)
        requests.post(url, data=TEST_MESSAGE, auth=TEST_AUTH)


@pytest.fixture(scope="session")
def dd_environment():
    envs = {'JMX_PORT': str(JMX_PORT)}
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file,
        log_patterns=['ActiveMQ Jolokia REST API available'],
        conditions=[
            WaitForPortListening(HOST, TEST_PORT),
            populate_server,
        ],
        env_vars=envs,
    ):
        config = load_jmx_config()
        config['instances'][0].update({
            'port': str(JMX_PORT),
            'host': HOST
        })
        yield config, {'use_jmx': True}
