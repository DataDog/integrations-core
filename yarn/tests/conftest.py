# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from copy import deepcopy
from urllib.parse import urljoin

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.yarn import YarnCheck
from datadog_checks.yarn.yarn import YARN_APPS_PATH, YARN_CLUSTER_METRICS_PATH, YARN_NODES_PATH, YARN_SCHEDULER_PATH

from .common import (
    FIXTURE_DIR,
    HERE,
    INSTANCE_INTEGRATION,
    YARN_APPS_URL,
    YARN_CLUSTER_METRICS_URL,
    YARN_NODES_URL,
    YARN_SCHEDULER_URL,
)


@pytest.fixture(scope="session")
def dd_environment():
    conditions = [
        CheckEndpoints(urljoin(INSTANCE_INTEGRATION['resourcemanager_uri'], endpoint), attempts=240)
        for endpoint in (YARN_APPS_PATH, YARN_CLUSTER_METRICS_PATH, YARN_NODES_PATH, YARN_SCHEDULER_PATH)
    ]

    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        mount_logs=True,
        conditions=conditions,
        sleep=30,
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def check():
    return lambda instance: YarnCheck('yarn', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)


@pytest.fixture
def mocked_request(fake_http_response):
    for url, fixture in (
        (YARN_CLUSTER_METRICS_URL, 'cluster_metrics'),
        (YARN_APPS_URL, 'apps_metrics'),
        (YARN_NODES_URL, 'nodes_metrics'),
        (YARN_SCHEDULER_URL, 'scheduler_metrics'),
    ):
        with open(os.path.join(FIXTURE_DIR, fixture)) as f:
            fake_http_response(url, json_data=json.load(f))
