# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks


def test_e2e_openmetrics_v2(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_service_check('argo_rollouts.openmetrics.health', ServiceCheck.OK, count=1)
    assert_service_checks(aggregator)
