# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Pytest fixtures for external_dns integration tests.

Provides fixtures for:
- OpenMetrics V1 (legacy) and V2 instance configurations
- Mock HTTP responses for external-dns v1.15.0 (legacy) and v1.20.0
- E2E test environment (mock-based, no Docker)
"""

import os
from copy import deepcopy

import pytest

from .common import FIXTURE_DIR

URL = 'http://localhost:7979/metrics'

# OpenMetrics V1 (legacy) instance configuration using prometheus_url
INSTANCE_OMV1 = {'prometheus_url': URL, 'tags': ['custom:tag']}

# OpenMetrics V2 instance configuration using openmetrics_endpoint
INSTANCE_OMV2 = {'openmetrics_endpoint': URL, 'tags': ['custom:tag']}


@pytest.fixture(scope='session')
def dd_environment():
    """E2E test environment fixture (mock-based, no Docker)."""
    yield deepcopy(INSTANCE_OMV1)


@pytest.fixture(scope='session')
def instance():
    """Session-scoped instance for E2E tests."""
    return deepcopy(INSTANCE_OMV1)


@pytest.fixture
def instance_omv1():
    """Instance configuration for OpenMetrics V1 (legacy) integration."""
    return deepcopy(INSTANCE_OMV1)


@pytest.fixture
def instance_omv2():
    """Instance configuration for OpenMetrics V2 integration."""
    return deepcopy(INSTANCE_OMV2)


@pytest.fixture
def mock_http_response_v115(mock_http_response):
    """Mock HTTP response with external-dns v1.15.0 (legacy) metrics."""
    metric_file_path = os.path.join(FIXTURE_DIR, 'metrics-legacy.txt')
    yield mock_http_response(file_path=metric_file_path)


@pytest.fixture
def mock_http_response_v120(mock_http_response):
    """Mock HTTP response with external-dns v1.20.0 metrics."""
    metric_file_path = os.path.join(FIXTURE_DIR, 'metrics-1.18.txt')
    yield mock_http_response(file_path=metric_file_path)
