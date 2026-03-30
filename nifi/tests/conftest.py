# ABOUTME: Pytest fixtures for NiFi integration tests.
# ABOUTME: Provides dd_environment for Docker-based tests and instance fixtures.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {}
