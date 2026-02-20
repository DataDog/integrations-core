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
