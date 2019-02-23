# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname
from datadog_checks.php_fpm import PHPFPMCheck


HOST = get_docker_hostname()
HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_INSTANCE = {
    'status_url': 'http://{}:8080/some_status'.format(HOST),
    'ping_url': 'http://{}:8080/some_ping'.format(HOST),
}

INSTANCE_FASTCGI = {
    'status_url': 'http://{}:9000/some_status'.format(HOST),
    'ping_url': 'http://{}:9000/some_ping'.format(HOST),
    'use_fastcgi': True,
}


@pytest.fixture
def check():
    return PHPFPMCheck('php_fpm', {}, {})


@pytest.fixture
def instance():
    return deepcopy(DEFAULT_INSTANCE)


@pytest.fixture
def instance_fastcgi():
    return deepcopy(INSTANCE_FASTCGI)


@pytest.fixture
def ping_url_tag():
    return 'ping_url:http://{}:8080/some_ping'.format(HOST)


@pytest.fixture
def ping_url_tag_fastcgi():
    return 'ping_url:http://{}:9000/some_ping'.format(HOST)


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yml'),
        endpoints='http://{}:8080'.format(HOST)
    ):
        yield DEFAULT_INSTANCE


@pytest.fixture
def payload():
    """
    example payload from /status?json
    """
    return json.loads("""{
        "pool":"www",
        "process manager":"dynamic",
        "start time":1530722898,
        "start since":12,
        "accepted conn":2,
        "listen queue":0,
        "max listen queue":0,
        "listen queue len":128,
        "idle processes":1,
        "active processes":1,
        "total processes":2,
        "max active processes":1,
        "max children reached":0,
        "slow requests":0
    }""")
