# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks

from . import common


@pytest.mark.e2e
@pytest.mark.usefixtures("dd_environment")
def test_e2e(instance, aggregator, dd_agent_check):
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_service_check('duckdb.can_connect', ServiceCheck.OK)
    assert_service_checks(aggregator)
