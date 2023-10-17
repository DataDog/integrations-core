# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import pytest
from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return copy.deepcopy(common.INSTANCE_MOCK)