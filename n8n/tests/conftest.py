# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckEndpoints(common.INSTANCE["openmetrics_endpoint"]),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [common.INSTANCE],
        }


@pytest.fixture
def instance():
    return copy.deepcopy(common.INSTANCE)
