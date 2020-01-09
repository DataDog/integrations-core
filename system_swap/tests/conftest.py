# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.system_swap import SystemSwap

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield common.INSTANCE


@pytest.fixture
def check():
    return SystemSwap('system_swap', {}, {})


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)
