# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from .common import COMPOSE_FILE, MOCKED_INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = COMPOSE_FILE
    conditions = [
        CheckEndpoints(MOCKED_INSTANCE["openmetrics_endpoint"]),
    ]
    logging.info(conditions)
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [MOCKED_INSTANCE],
        }


@pytest.fixture
def instance():
    return MOCKED_INSTANCE
