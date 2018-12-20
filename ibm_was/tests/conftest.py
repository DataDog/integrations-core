# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture(scope="session")
def instance():
    return common.INSTANCE
