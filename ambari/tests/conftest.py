# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {
        'url': 'localhost',
        'port': 80,
        'username': 'admin',
        'password': 'admin',
    }


@pytest.fixture
def authentication():
    return {'username': 'admin', 'password': 'admin'}
