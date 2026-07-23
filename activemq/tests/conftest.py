# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import base64
import http.cookiejar
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import pytest

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


def basic_auth_header(auth: tuple[str, str]) -> str:
    token = '{}:{}'.format(*auth).encode('utf-8')
    return 'Basic {}'.format(base64.b64encode(token).decode('ascii'))


def open_url_without_status_error(req: urllib.request.Request, opener: Any = None) -> Any:
    try:
        if opener is not None:
            return opener.open(req)
        return urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        return e


def populate_server():
    """Add some queues and topics to ensure more metrics are available."""
    time.sleep(3)

    auth_header = basic_auth_header(TEST_AUTH)

    if IS_ARTEMIS:
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        headers = {'Accept': 'application/json', 'Origin': BASE_URL, 'Authorization': auth_header}
        req = urllib.request.Request(ARTEMIS_URL + '/list', headers=headers)
        response = open_url_without_status_error(req, opener=opener)
        try:
            channels = json.load(response)['value']['org.apache.activemq.artemis']
        finally:
            response.close()
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
            req = urllib.request.Request(
                ARTEMIS_URL + '/exec',
                data=json.dumps(body).encode('utf-8'),
                headers={**headers, 'Content-Type': 'application/json'},
                method='POST',
            )
            open_url_without_status_error(req, opener=opener).close()

    else:
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = urllib.parse.urlencode(TEST_MESSAGE).encode('utf-8')
        for queue in TEST_QUEUES:
            url = '{}/{}?type=queue'.format(ACTIVEMQ_URL, queue)
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            open_url_without_status_error(req).close()

        for topic in TEST_TOPICS:
            url = '{}/{}?type=topic'.format(ACTIVEMQ_URL, topic)
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            open_url_without_status_error(req).close()


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
