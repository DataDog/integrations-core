# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.network import Network

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield common.INSTANCE, common.E2E_METADATA


@pytest.fixture
def check():
    return lambda instance: Network(common.SERVICE_CHECK_NAME, {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)


@pytest.fixture
def instance_blacklist():
    return deepcopy(common.INSTANCE_BLACKLIST)
