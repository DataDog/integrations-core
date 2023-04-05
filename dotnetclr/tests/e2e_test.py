# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.dev.testing import requires_py3
from datadog_checks.dotnetclr import DotnetclrCheckV2

from .common import MINIMAL_INSTANCE

pytestmark = pytest.mark.e2e


@requires_py3
def test(dd_agent_check):
    aggregator = dd_agent_check(MINIMAL_INSTANCE, rate=True)
    aggregator.assert_service_check('dotnetclr.windows.perf.health', DotnetclrCheckV2.OK)
