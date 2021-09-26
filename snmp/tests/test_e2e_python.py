# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.snmp import SnmpCheck

from . import common

pytestmark = pytest.mark.e2e


@common.snmp_integration_only
def test_e2e_python(dd_agent_check):
    metrics = common.SUPPORTED_METRIC_TYPES
    config = common.generate_container_instance_config(metrics)
    instance = config['instances'][0]
    aggregator = dd_agent_check(config, rate=True)
    tags = ['snmp_device:{}'.format(instance['ip_address'])]

    # Test metrics
    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=tags)
    aggregator.assert_metric('snmp.sysUpTimeInstance')

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=tags, at_least=1)

    common.assert_common_metrics(aggregator, is_e2e=True)
    aggregator.all_metrics_asserted()
