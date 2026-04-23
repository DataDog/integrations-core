# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

CHECK_NAME = 'lparstats'


@pytest.fixture(scope='session')
def dd_environment():
    # lparstats uses lparstat which is only available on AIX; no external
    # service or container is needed for e2e tests.
    yield


@pytest.fixture
def instance():
    return {
        'name': CHECK_NAME,
        'memory_stats': True,
        'page_stats': False,
        'memory_entitlements': False,
        'hypervisor': False,
        'spurr_utilization': True,
    }
