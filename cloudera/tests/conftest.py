# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy

import mock
import pytest
from packaging.version import Version

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


class MockCmClient:
    def __init__(self, log, **kwargs):
        self.log = log
        self.kwargs = kwargs

    def get_version(self):
        return Version('7.0.0')

    def read_clusters(self):
        return []

    def read_events(self, query):
        return []


@pytest.fixture
def cloudera_cm_client():
    def cm_client(log, **kwargs):
        return MockCmClient(log, **kwargs)

    with mock.patch('datadog_checks.cloudera.client.factory.CmClient', side_effect=cm_client) as mock_cm_client:
        yield mock_cm_client
