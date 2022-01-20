# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

# from .common import instance
INSTANCE = {'server': 'localhost', 'username': 'admin', 'password': 'admin', 'site': 'test', 'app_pools': 'test'}


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    aggregator = dd_agent_check(instance)
    aggregator.assert_service_check('iis.windows.perf.health')
