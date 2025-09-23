# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.docker import using_windows_containers
from datadog_checks.dev.utils import ON_WINDOWS

from .metrics import CORE_COUNTS, CORE_GAUGES, CORE_RATES, UNIX_GAUGES

E2E_METADATA = {'docker_platform': 'windows' if using_windows_containers() else 'linux'}


@pytest.fixture(scope='session')
def dd_environment(instance_basic_volume):
    yield instance_basic_volume, E2E_METADATA


@pytest.fixture(scope='session')
def instance_basic_volume():
    return {'use_mount': 'false', 'tag_by_label': False}


@pytest.fixture(scope='session')
def instance_basic_mount():
    return {'use_mount': 'true', 'tag_by_label': False}


@pytest.fixture(scope='session')
def gauge_metrics():
    if ON_WINDOWS:
        return CORE_GAUGES
    else:
        return UNIX_GAUGES


@pytest.fixture(scope='session')
def rate_metrics():
    return CORE_RATES


@pytest.fixture(scope='session')
def count_metrics():
    return CORE_COUNTS
