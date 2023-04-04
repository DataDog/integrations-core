# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.testing import requires_py3
from datadog_checks.dotnetclr.check import DotnetclrCheck


@pytest.mark.e2e
@requires_py3
def test_e2e_py3(dd_agent_check, aggregator, instance):
    aggregator = dd_agent_check(instance)
    aggregator.assert_service_check('dotnetclr.windows.perf.health', DotnetclrCheckV2.CRITICAL)
