# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
from tests.metrics import (
    IF_COUNTS,
    IF_GAUGES,
    IF_RATES,
    IP_COUNTS,
    IP_IF_COUNTS,
    IPX_COUNTS,
    TCP_COUNTS,
    TCP_GAUGES,
    UDP_COUNTS,
)

from datadog_checks.snmp import SnmpCheck

from . import common


def _build_device_ip(container_ip):
    snmp_device = container_ip.split('.')
    snmp_device[len(snmp_device) - 1] = '1'
    snmp_device = '.'.join(snmp_device)
    return snmp_device


@pytest.mark.e2e
@common.python_autodiscovery_only
def test_e2e_python(dd_agent_check):
    metrics = common.SUPPORTED_METRIC_TYPES
    instance = common.generate_container_instance_config(metrics)
    aggregator = dd_agent_check(instance, rate=True)
    tags = ['snmp_device:{}'.format(instance['ip_address'])]

    # Test metrics
    for metric in common.SUPPORTED_METRIC_TYPES:
        metric_name = "snmp." + metric['name']
        aggregator.assert_metric(metric_name, tags=tags)
    aggregator.assert_metric('snmp.sysUpTimeInstance')

    # Test service check
    aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=tags, at_least=1)

    common.assert_common_metrics(aggregator)
    aggregator.all_metrics_asserted()


@pytest.mark.e2e
@common.agent_autodiscovery_only
def test_e2e_agent_autodiscovery(dd_agent_check, container_ip):
    snmp_device = _build_device_ip(container_ip)
    aggregator = dd_agent_check({'init_config': {}, 'instances': []}, rate=True)
    common_tags = [
        'snmp_profile:generic-router',
        'snmp_device:{}'.format(snmp_device),
        'autodiscovery_subnet:{}/28'.format(container_ip),
    ]

    common.assert_common_metrics(aggregator, common_tags)

    for interface in ['eth0', 'eth1']:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags, count=1)
        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)
    for metric in TCP_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=common_tags, count=1)
    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=2)
    for metric in UDP_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=common_tags, count=1)
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in IP_COUNTS + IPX_COUNTS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags, count=1)
        for metric in IP_IF_COUNTS:
            for interface in ['17', '21']:
                tags = ['ipversion:{}'.format(version), 'interface:{}'.format(interface)] + common_tags
                aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()
