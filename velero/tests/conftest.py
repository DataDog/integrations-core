# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import MOCKED_INSTANCE

@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return MOCKED_INSTANCE
