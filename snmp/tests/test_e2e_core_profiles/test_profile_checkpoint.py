# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_all_profile_metrics_and_tags_covered,
    assert_common_metrics,
    assert_extend_checkpoint_firewall_cpu_memory,
    assert_extend_generic_if,
    assert_extend_generic_ip,
    assert_extend_generic_tcp,
    assert_extend_generic_udp,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_checkpoint(dd_agent_check):
    profile = 'checkpoint'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:checkpoint',
        'snmp_host:checkpoint.device.name',
        'device_hostname:checkpoint.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
        'device_vendor:checkpoint',
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_tcp(aggregator, common_tags)
    assert_extend_generic_udp(aggregator, common_tags)
    assert_extend_generic_ip(aggregator, common_tags)
    assert_extend_checkpoint_firewall_cpu_memory(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric(
        'snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + ['cpu:7097', 'cpu_core:7097']
    )
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fwAccepted', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.fwDropped', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.fwNumConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fwPeakNumConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fwRejected', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.memActiveReal64', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memActiveVirtual64', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memFreeReal64', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memTotalReal64', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memTotalVirtual64', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.procNum', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['cpu_core:13039'],
        ['cpu_core:13761'],
        ['cpu_core:28994'],
        ['cpu_core:29751'],
        ['cpu_core:33826'],
        ['cpu_core:40053'],
        ['cpu_core:48847'],
        ['cpu_core:61593'],
        ['cpu_core:65044'],
        ['cpu_core:7097'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.multiProcIdleTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.multiProcSystemTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.multiProcUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.multiProcUserTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['disk_index:0', 'disk_name:first'],
        ['disk_index:1', 'disk_name:second'],
        ['disk_index:2', 'disk_name:third'],
        ['disk_index:3', 'disk_name:fourth'],
        ['disk_index:4', 'disk_name:fifth'],
        ['disk_index:5', 'disk_name:sixth'],
        ['disk_index:6', 'disk_name:seventh'],
        ['disk_index:7', 'disk_name:eighth'],
        ['disk_index:8', 'disk_name:ninth'],
        ['disk_index:9', 'disk_name:tenth'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.multiDiskFreeAvailableBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.multiDiskFreeAvailablePercent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.multiDiskFreeTotalBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.multiDiskFreeTotalPercent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.multiDiskSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.multiDiskUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['sensor_index:0', 'sensor_name:first'],
        ['sensor_index:1', 'sensor_name:second'],
        ['sensor_index:2', 'sensor_name:third'],
        ['sensor_index:3', 'sensor_name:fourth'],
        ['sensor_index:4', 'sensor_name:fifth'],
        ['sensor_index:5', 'sensor_name:sixth'],
        ['sensor_index:6', 'sensor_name:seventh'],
        ['sensor_index:7', 'sensor_name:eighth'],
        ['sensor_index:8', 'sensor_name:ninth'],
        ['sensor_index:9', 'sensor_name:tenth'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fanSpeedSensorStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fanSpeedSensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fan_speed_sensor_status:false', 'sensor_index:0', 'sensor_name:first'],
        ['fan_speed_sensor_status:false', 'sensor_index:3', 'sensor_name:fourth'],
        ['fan_speed_sensor_status:false', 'sensor_index:6', 'sensor_name:seventh'],
        ['fan_speed_sensor_status:false', 'sensor_index:9', 'sensor_name:tenth'],
        ['fan_speed_sensor_status:reading_error', 'sensor_index:2', 'sensor_name:third'],
        ['fan_speed_sensor_status:reading_error', 'sensor_index:5', 'sensor_name:sixth'],
        ['fan_speed_sensor_status:reading_error', 'sensor_index:8', 'sensor_name:ninth'],
        ['fan_speed_sensor_status:true', 'sensor_index:1', 'sensor_name:second'],
        ['fan_speed_sensor_status:true', 'sensor_index:4', 'sensor_name:fifth'],
        ['fan_speed_sensor_status:true', 'sensor_index:7', 'sensor_name:eighth'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fanSpeedSensor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['sensor_index:0', 'sensor_name:first'],
        ['sensor_index:1', 'sensor_name:second'],
        ['sensor_index:2', 'sensor_name:third'],
        ['sensor_index:3', 'sensor_name:fourth'],
        ['sensor_index:4', 'sensor_name:fifth'],
        ['sensor_index:5', 'sensor_name:sixth'],
        ['sensor_index:6', 'sensor_name:seventh'],
        ['sensor_index:7', 'sensor_name:eighth'],
        ['sensor_index:8', 'sensor_name:ninth'],
        ['sensor_index:9', 'sensor_name:tenth'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.tempertureSensorStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.tempertureSensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'Linux host1 3.10.0-957.21.3cpx86_64 #1 SMP Tue Jan 28 17:26:12 IST 2020 x86_64',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'model': 'Check Point 3200',
        'name': 'checkpoint.device.name',
        'os_name': 'Gaia',
        'os_version': '3.10.0',
        'product_name': 'SVN Foundation',
        'profile': 'checkpoint',
        'serial_number': '1711BA4008',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2620.1.1',
        'vendor': 'checkpoint',
        'version': 'R80.10',
        'tags': common_tags,
        'device_type': 'firewall',
    }
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
