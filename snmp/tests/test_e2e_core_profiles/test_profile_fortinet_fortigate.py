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
    assert_extend_fortinet_fortigate_cpu_memory,
    assert_extend_fortinet_fortigate_vpn_tunnel,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_fortinet_fortigate(dd_agent_check):
    profile = 'fortinet-fortigate'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:fortinet-fortigate',
        'snmp_host:fortinet-fortigate.device.name',
        'device_hostname:fortinet-fortigate.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
        'device_vendor:fortinet',
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_fortinet_fortigate_cpu_memory(aggregator, common_tags)
    assert_extend_fortinet_fortigate_vpn_tunnel(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_metric('snmp.fgApHTTPConnections', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgApHTTPMaxConnections', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysCpuUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysDiskCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysDiskUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysLowMemCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysLowMemUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysMemCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysMemUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysSes6Count', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysSes6Rate1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysSesCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgSysSesRate1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgVdMaxVdoms', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fgVdNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['processor_index:12'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.fgProcessorPktDroppedCount', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.fgProcessorPktDroppedCount.rate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.fgProcessorPktRxCount', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.fgProcessorPktRxCount.rate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.fgProcessorPktTxCount', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.fgProcessorPktTxCount.rate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['processor_index:12'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fgProcessorSysUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgProcessorUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['virtualdomain_index:4', 'virtualdomain_name:their oxen quaintly'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fgVdEntCpuUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgVdEntHaState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgVdEntMemUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgVdEntOpMode', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgVdEntSesCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgVdEntSesRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    phase1_name = [
        'ESMAO-Lomtec',
        'ESMAO',
    ]
    for name in phase1_name:
        tags = common_tags + ['vpn_tunnel:' + name]
        aggregator.assert_metric('snmp.fgVpnTunEntInOctets', metric_type=aggregator.GAUGE, tags=tags)
        aggregator.assert_metric('snmp.fgVpnTunEntOutOctets', metric_type=aggregator.GAUGE, tags=tags)
        aggregator.assert_metric('snmp.fgVpnTunEntStatus', metric_type=aggregator.GAUGE, tags=tags)

    tag_rows = [
        ['virtualdomain_index:4', 'virtualdomain_name:their oxen quaintly', 'virtualdomain_state:secondary'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fgVirtualDomain', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['virtualdomain_index:4', 'interface:le0'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fgIntfEntVdom', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['policy_index:22', 'virtualdomain_index:2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fgFwPolByteCount', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgFwPolByteCount.rate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgFwPolPktCount', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgFwPolPktCount.rate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['policy6_index:29', 'virtualdomain_index:5'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fgFwPol6ByteCount', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.fgFwPol6ByteCount.rate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.fgFwPol6PktCount', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.fgFwPol6PktCount.rate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'model': 'FGT_501E',
        'name': 'fortinet-fortigate.device.name',
        'os_name': 'FortiOS',
        'os_version': '5.6.4',
        'product_name': 'FortiGate-501E',
        'profile': 'fortinet-fortigate',
        'serial_number': 'FG5H1E5110000000',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.12356.101.1.1',
        'vendor': 'fortinet',
        'version': 'v5.6.4,build1575b1575,180425 (GA)',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
