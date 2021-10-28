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

from .common import (
    ACTIVEMQ_URL,
    ARTEMIS_URL,
    BASE_URL,
    COMPOSE_FILE,
    HERE,
    HOST,
    IS_ARTEMIS,
    JMX_PORT,
    TEST_AUTH,
    TEST_MESSAGE,
    TEST_PORT,
    TEST_QUEUES,
    TEST_TOPICS,
)


def populate_server():
    """Add some queues and topics to ensure more metrics are available."""
    time.sleep(3)

    if IS_ARTEMIS:
        s = requests.Session()
        s.auth = TEST_AUTH
        s.headers = {'accept': 'application/json', 'origin': BASE_URL}
        data = s.get(ARTEMIS_URL + '/list')
        channels = data.json()['value']['org.apache.activemq.artemis']
        broker = [k for k in channels.keys() if k.startswith('broker') and ',' not in k][0]
        bean = 'org.apache.activemq.artemis:{}'.format(broker)

        for queue in TEST_QUEUES:
            body = {
                "type": "exec",
                "mbean": bean,
                "operation": "createQueue("
                "java.lang.String,"
                "java.lang.String,"
                "java.lang.String,"
                "java.lang.String,"
                "boolean,int,boolean,boolean)",
                "arguments": ["activemq.notifications", "ANYCAST", queue, None, True, -1, False, True],
            }
            s.post(ARTEMIS_URL + '/exec', json=body)

    else:
        for queue in TEST_QUEUES:
            url = '{}/{}?type=queue'.format(ACTIVEMQ_URL, queue)
            requests.post(url, data=TEST_MESSAGE, auth=TEST_AUTH)

        for topic in TEST_TOPICS:
            url = '{}/{}?type=topic'.format(ACTIVEMQ_URL, topic)
            requests.post(url, data=TEST_MESSAGE, auth=TEST_AUTH)


@pytest.fixture(scope="session")
def dd_environment():
    envs = {'JMX_PORT': str(JMX_PORT)}

    log_pattern = 'ActiveMQ Jolokia REST API available'
    if IS_ARTEMIS:
        log_pattern = 'HTTP Server started at http://0.0.0.0:8161'

    with docker_run(
        os.path.join(HERE, 'compose', COMPOSE_FILE),
        log_patterns=[log_pattern],
        conditions=[WaitForPortListening(HOST, TEST_PORT), populate_server],
        env_vars=envs,
    ):
        config = load_jmx_config()
        config['instances'][0].update({'port': str(JMX_PORT), 'host': HOST})
        yield config, {'use_jmx': True}
