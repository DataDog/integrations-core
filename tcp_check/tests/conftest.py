# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.tcp_check import TCPCheck

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield common.INSTANCE


@pytest.fixture
def check():
    return TCPCheck(common.CHECK_NAME, {}, [common.INSTANCE])


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)
