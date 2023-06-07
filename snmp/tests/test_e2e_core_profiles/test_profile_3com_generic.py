# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.dev.docker import get_container_ip
from tests.common import SNMP_CONTAINER_NAME

from .. import common, metrics

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_3com_generic(dd_agent_check):
    config = common.generate_container_instance_config([])
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'meraki-cloud-controller',
        }
    )
    # run a rate check, will execute two check runs to evaluate rate metrics
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_container_ip(SNMP_CONTAINER_NAME)
    common_tags = [
        'snmp_profile:meraki-cloud-controller',
        'snmp_host:dashboard.meraki.com',
        'device_vendor:meraki',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ]

    common.assert_common_metrics(aggregator, tags=common_tags, is_e2e=True, loader='core')

    dev_metrics = ['devStatus', 'devClientCount']
    dev_tags = ['product:MR16-HW', 'network:L_NETWORK', 'mac_address:02:02:00:66:f5:7f'] + common_tags
    for metric in dev_metrics:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=dev_tags, count=2, device='Gymnasium'
        )

    if_tags = ['interface:wifi0', 'index:4', 'mac_address:02:02:00:66:f5:00'] + common_tags
    if_metrics = ['devInterfaceSentPkts', 'devInterfaceRecvPkts', 'devInterfaceSentBytes', 'devInterfaceRecvBytes']
    for metric in if_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=2)

    # IF-MIB
    if_tags = ['interface:eth0'] + common_tags
    for metric in metrics.IF_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=if_tags, count=1)

    for metric in metrics.IF_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=2)

    for metric in metrics.IF_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    for metric in metrics.IF_BANDWIDTH_USAGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    custom_speed_tags = if_tags + ['speed_source:device']
    for metric in metrics.IF_CUSTOM_SPEED_GAUGES:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=custom_speed_tags, count=2
        )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=2, tags=common_tags)
    aggregator.assert_metric(
        'snmp.interface.status',
        metric_type=aggregator.GAUGE,
        tags=if_tags + ['interface_index:11', 'status:warning', 'admin_status:down', 'oper_status:lower_layer_down'],
        value=1,
    )
    aggregator.assert_all_metrics_covered()
