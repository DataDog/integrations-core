# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from . import common

E2E_METADATA = {
    'start_commands': [
        'pip install duckdb==1.1.1',
    ]
}


@pytest.fixture(scope='session')
def dd_environment():
    yield common.DEFAULT_INSTANCE, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(common.DEFAULT_INSTANCE)
