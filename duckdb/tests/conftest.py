# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import duckdb
import pytest

from datadog_checks.dev import WaitFor

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield common.DEFAULT_INSTANCE


@pytest.fixture
def instance():
    return deepcopy(common.DEFAULT_INSTANCE)
