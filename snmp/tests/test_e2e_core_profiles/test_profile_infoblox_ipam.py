# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_host_resources_base,
    assert_extend_generic_if,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_infoblox_ipam(dd_agent_check):
    config = create_e2e_core_test_config('infoblox-ipam')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:infoblox-ipam',
        'snmp_host:infoblox-ipam.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + ['ib_hardware_type:forward quaintly acted',
 'ib_nios_version:forward their acted forward acted kept quaintly',
 'ib_serial_number:forward zombies Jaded oxen quaintly driving']

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibDDNSUpdateFailure', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ibDDNSUpdatePrerequisiteReject', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ibDDNSUpdateReject', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ibDDNSUpdateSuccess', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ibDhcpDeferredQueueSize', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibDnsQueryRate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
         ['ib_bind_zone_name:acted'],
         ['ib_bind_zone_name:driving acted driving driving'],
         ['ib_bind_zone_name:forward oxen driving'],
         ['ib_bind_zone_name:quaintly zombies zombies'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibBindZoneFailure', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ibBindZoneNxDomain', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ibBindZoneNxRRset', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ibBindZoneRecursion', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ibBindZoneReferral', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ibBindZoneSuccess', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    tag_rows = [
         ['ib_node_ip_address:driving', 'ib_node_replication_status:oxen Jaded but forward Jaded acted oxen'],
         ['ib_node_ip_address:kept kept but', 'ib_node_replication_status:forward oxen quaintly oxen driving forward their acted forward'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibNodeQueueFromMaster', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ibNodeQueueToMaster', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['ib_service_description:quaintly Jaded quaintly driving driving', 'ib_service_name:radius', 'ib_service_status:working'],
         ['ib_service_description:their quaintly but acted', 'ib_service_name:memory', 'ib_service_status:failed'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibMemberServiceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'infoblox-ipam Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'infoblox-ipam.device.name',
        'profile': 'infoblox-ipam',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.7779.3.7',
        'vendor': 'infoblox',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
