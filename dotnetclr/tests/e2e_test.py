# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import MINIMAL_INSTANCE

pytestmark = pytest.mark.e2e


@pytest.mark.flaky
def test(dd_agent_check):
    from datadog_checks.dotnetclr.check import DotnetclrCheckV2

    aggregator = dd_agent_check(MINIMAL_INSTANCE, rate=True)
    aggregator.assert_service_check('dotnetclr.windows.perf.health', DotnetclrCheckV2.OK)
