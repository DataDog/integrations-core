# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.testing import requires_py3
from datadog_checks.iis import IIS


pytestmark = [requires_py3]


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance, check):
    aggregator = dd_agent_check(instance)
    aggregator.assert_service_check('iis.windows.perf.health', IIS.CRITICAL)
