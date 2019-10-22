# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def agent_instance():
    return {
        'agent_endpoint': 'localhost:9090/metrics',
        'tags': ['pod_test']
    }


@pytest.fixture
def operator_instance():
    return {
        'agent_endpoint': ' localhost:6942/metrics', 
        'tags': ['operator_test']
    }