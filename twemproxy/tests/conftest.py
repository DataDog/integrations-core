# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.twemproxy import Twemproxy

from . import common


def send_request(http_request: Request) -> None:
    try:
        with urlopen(http_request) as response:
            response.read()
    except HTTPError as e:
        with e:
            e.read()


def put_etcd_value(key: str, value: str) -> None:
    send_request(
        Request(
            'http://{}:2379/v2/keys/{}'.format(common.HOST, key),
            data=urlencode({'value': value}).encode('utf-8'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            method='PUT',
        )
    )


def setup_post_data():
    put_etcd_value('services/redis/01', 'redis1:6101')
    put_etcd_value('services/redis/02', 'redis2:6102')
    put_etcd_value('services/twemproxy/port', '6100')
    put_etcd_value('services/twemproxy/host', 'localhost')


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        common.COMPOSE_FILE,
        service_name="etcd0",
        conditions=[CheckDockerLogs(common.COMPOSE_FILE, 'Ready to accept connections'), setup_post_data],
        mount_logs=True,
        attempts=2,
    ):
        with docker_run(common.COMPOSE_FILE, log_patterns="listening on stats server", attempts=2):
            yield common.INSTANCE


@pytest.fixture
def check():
    check = Twemproxy('twemproxy', {}, {})
    return check


@pytest.fixture
def instance():
    return common.INSTANCE


@pytest.fixture
def setup_request():
    """
    A request needs to be made in order for some of the data to be seeded
    """
    url = "http://{}:{}".format(common.HOST, common.PORT)
    try:
        send_request(Request(url, method='GET'))
    except Exception:
        pass
