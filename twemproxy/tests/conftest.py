# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.twemproxy import Twemproxy

from . import common


def setup_post_data():
    requests.put('http://{}:2379/v2/keys/services/redis/01'.format(common.HOST), data={'value': 'redis1:6101'})
    requests.put('http://{}:2379/v2/keys/services/redis/02'.format(common.HOST), data={'value': 'redis2:6102'})
    requests.put('http://{}:2379/v2/keys/services/twemproxy/port'.format(common.HOST), data={'value': '6100'})
    requests.put('http://{}:2379/v2/keys/services/twemproxy/host'.format(common.HOST), data={'value': 'localhost'})


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
        requests.get(url)
    except Exception:
        pass
