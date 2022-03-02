# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from copy import deepcopy

CONFIG = {'host': 'localhost', 'user': 'user', 'password': 'password'}

@pytest.fixture(scope='session')
def dd_environment():
    yield CONFIG


@pytest.fixture
def instance():
    return deepcopy(CONFIG)
