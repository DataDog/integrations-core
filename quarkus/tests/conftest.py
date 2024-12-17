# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from pathlib import Path

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

INSTANCE = {'openmetrics_endpoint': 'http://localhost:8080/q/metrics'}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = str(Path(__file__).parent.absolute() / 'docker' / 'docker-compose.yaml')
    conditions = [
        CheckEndpoints(INSTANCE["openmetrics_endpoint"]),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [INSTANCE],
        }


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)
