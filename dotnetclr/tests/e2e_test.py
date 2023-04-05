# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3

from .common import INSTANCE

pytestmark = pytest.mark.e2e


@requires_py3
def test(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK)
