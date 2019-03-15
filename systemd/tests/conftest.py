# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .metrics import CORE_UNITS
from .common import CONFIG


@pytest.fixture(scope='session')
def dd_environment():
    yield CONFIG, "local"  # cannot run the e2e tests - cannot call D-Bus inside a container


@pytest.fixture
def instance_ko():
    return {
        'units': [
            "nonexisting.service"
        ],
        'report_status': False,
        'report_process': False
    }


@pytest.fixture
def instance():
    return {
        'units': [
            "ssh.service",
            "cron.service",
            "networking.service"
        ],
        'report_status': False,
        'report_processes': True
    }


@pytest.fixture
def instance_collect_all():
    return {
        'units': [
            "ssh.service"
        ],
        'report_status': True,
        'report_processes': True
    }


@pytest.fixture
def instance_with_at_symbol():
    return {
        'units': [
            "..."
        ],
        'report_status': False,
        'report_process': False
    }


@pytest.fixture(scope='session')
def gauge_metrics():
    return CORE_UNITS
