# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
from collections.abc import Callable
from typing import Any

import pytest

from datadog_checks.dcgm import DcgmCheck
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(common.INSTANCE["openmetrics_endpoint"]),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [common.INSTANCE],
        }


@pytest.fixture
def instance():
    return copy.deepcopy(common.INSTANCE)


# For Unit Test:
@pytest.fixture
def check(instance):
    return DcgmCheck('dcgm.', {}, [instance])


def serve_fixture(fake_http_response: Callable[..., Any], name: str) -> None:
    with open(os.path.join(os.path.dirname(__file__), 'fixtures', name), 'rb') as f:
        fake_http_response(common.INSTANCE['openmetrics_endpoint'], f.read(), headers={'Content-Type': 'text/plain'})


@pytest.fixture()
def mock_metrics(fake_http_response):
    serve_fixture(fake_http_response, 'metrics.txt')


@pytest.fixture()
def mock_label_remap(fake_http_response):
    serve_fixture(fake_http_response, 'label_remap.txt')
