# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.ecs_fargate import FargateCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    aggregator = dd_agent_check(instance)
    aggregator.assert_service_check("fargate_check", status=FargateCheck.CRITICAL, tags=[], count=1)
