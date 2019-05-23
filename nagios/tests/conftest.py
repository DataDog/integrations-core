# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from copy import deepcopy

from datadog_checks.nagios import NagiosCheck

from .common import (
    INSTANCE_INTEGRATION,
    E2E_METADATA
)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator

    aggregator.reset()
    return aggregator


@pytest.fixture(scope="session")
def dd_environment():
    return INSTANCE_INTEGRATION, E2E_METADATA


@pytest.fixture
def check():
    return NagiosCheck('nagios', {}, {}, instances=[INSTANCE_INTEGRATION])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
