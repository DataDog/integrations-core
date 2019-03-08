# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from .metrics import CORE_GAUGES
from .common import CONFIG

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def systemctl_mocks():
    mock_systemctl = mock.patch('Unit(unit_id)', return_value=MockSystemdUnit(), __name__='unit_state')
    return mock_systemctl


@pytest.fixture(scope='session')
def dd_environment():
    yield CONFIG, "local"  # cannot run the e2e tests due to not being able to


@pytest.fixture
def instance_ko():
    return {
        'units': [
            "nonexisting.service"
        ],
        'collect_all_units': False
    }


@pytest.fixture
def instance():
    return {
        'units': [
            "ssh.service",
            "cron.service",
            "networking.service"
        ],
        'collect_all_units': False
    }


@pytest.fixture
def instance_collect_all():
    return {
        'units': [
            "ssh.service"
        ],
        'collect_all_units': True
    }


@pytest.fixture(scope='session')
def gauge_metrics():
    return CORE_GAUGES
