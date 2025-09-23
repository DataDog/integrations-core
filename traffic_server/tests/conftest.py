# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import docker_run

from .common import COMPOSE_FILE, INSTANCE, INSTANCE_BAD_URL, INSTANCE_NO_URL, TRAFFIC_SERVER_URL


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(COMPOSE_FILE, endpoints=[TRAFFIC_SERVER_URL]):
        yield INSTANCE


@pytest.fixture
def instance():
    return INSTANCE


@pytest.fixture
def instance_no_url():
    return INSTANCE_NO_URL


@pytest.fixture
def instance_bad_url():
    return INSTANCE_BAD_URL
