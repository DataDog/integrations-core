# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {
        'host': 'localhost',
        'port': 7222,
        'username': 'admin',
        'password': 'admin',
        'tags': ['optional:tag1'],
    }
