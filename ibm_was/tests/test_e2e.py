# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

from . import common

pytestmark = pytest.mark.e2e


def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)

    for metric_name in common.METRICS_ALWAYS_PRESENT:
        aggregator.assert_metric(metric_name)
        aggregator.assert_metric_has_tag(metric_name, 'key1:value1')

    aggregator.assert_service_check(
        'ibm_was.can_connect', status=AgentCheck.OK, tags=common.DEFAULT_SERVICE_CHECK_TAGS, count=1
    )
