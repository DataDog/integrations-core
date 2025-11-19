# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from . import common

SCRIPT_COMPLETION_STR = "Setup complete"


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckEndpoints(common.MOCKED_INSTANCE["openmetrics_endpoint"]),
        CheckDockerLogs("script-runner", SCRIPT_COMPLETION_STR),
    ]
    logging.info(conditions)
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [common.MOCKED_INSTANCE],
        }


@pytest.fixture
def instance():
    return copy.deepcopy(common.MOCKED_INSTANCE)
