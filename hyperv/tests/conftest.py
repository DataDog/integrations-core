# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from .common import INSTANCE_NO_REFRESH, INSTANCE_REFRESH


@pytest.fixture(scope='session')
def dd_environment():
    yield INSTANCE_REFRESH, 'local'


@pytest.fixture
def instance_refresh():
    return deepcopy(INSTANCE_REFRESH)


@pytest.fixture
def instance_no_refresh():
    return deepcopy(INSTANCE_NO_REFRESH)
