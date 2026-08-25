# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'headers': {'Authorization': 'Bearer test-token'},
    }


@pytest.fixture
def session_instance():
    return {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'control_m_username': 'workbench',
        'control_m_password': 'workbench',
    }
