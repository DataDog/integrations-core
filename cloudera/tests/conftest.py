# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy

import pytest

from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='cloudera', patterns=['server running']),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [common.INSTANCE],
            'init_config': common.INIT_CONFIG,
        }


@pytest.fixture
def config():
    return {
        'instances': [common.INSTANCE],
        'init_config': common.INIT_CONFIG,
    }


@pytest.fixture(scope='session')
def cloudera_check():
    return lambda instance: deepcopy(ClouderaCheck('cloudera', init_config=common.INIT_CONFIG, instances=[instance]))
