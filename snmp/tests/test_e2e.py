# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.snmp import SnmpCheck

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    metrics = common.SUPPORTED_METRIC_TYPES
    instance = common.generate_instance_config(metrics)
    aggregator = dd_agent_check(instance, rate=True)

    # Test metrics
    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=common.CHECK_TAGS)

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=common.CHECK_TAGS, at_least=1)

    aggregator.all_metrics_asserted()
