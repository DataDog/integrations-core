# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_if,
    assert_extend_entity_sensor_mib,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_nvidia_cumulus_linux_switch(dd_agent_check):
    config = create_e2e_core_test_config('nvidia-cumulus-linux-switch')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:nvidia-cumulus-linux-switch',
        'snmp_host:nvidia-cumulus-linux-switch.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    # TODO: Add assert_extend_* here:
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_entity_sensor_mib(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.egressAclCurrentCounters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.egressAclCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.egressAclCurrentMeters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.egressAclCurrentSlices', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.egressAclMaxCounters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.egressAclMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.egressAclMaxMeters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.egressAclMaxSlices', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ingressAclCurrentCounters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ingressAclCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ingressAclCurrentMeters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ingressAclCurrentSlices', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ingressAclMaxCounters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ingressAclMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ingressAclMaxMeters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ingressAclMaxSlices', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l2MacTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l2MacTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l3EcmpNextHopTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l3EcmpNextHopTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l3HostTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l3HostTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l3NextHopTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l3NextHopTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l3RoutingTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.l3RoutingTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memBuffer', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memCached', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.poeLastUpdateTime', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.poeTotalAvailablePower', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.poeTotalSystemPower', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.poeTotalUsedPower', metric_type=aggregator.GAUGE, tags=common_tags)

    tag_rows = [
         ['cl_port_name:their zombies'],
         ['cl_port_name:zombies zombies acted oxen but oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.clBufferOverflowDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clEgressNonQDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clEgressQOverflowDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clL3AclDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clL3v4InDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['cl_int_port_name:oxen'],
         ['cl_int_port_name:forward but'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.clIntInBcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInMcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInUcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutBcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutMcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutUcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['cl_int_pfc_port_name:forward kept quaintly quaintly driving oxen'],
         ['cl_int_pfc_port_name:driving Jaded driving Jaded kept oxen driving quaintly'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.clIntInPausePkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInPfc0Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInPfc1Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInPfc2Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInPfc3Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInPfc4Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInPfc5Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInPfc6Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntInPfc7Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutPausePkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutPfc0Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutPfc1Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutPfc2Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutPfc3Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutPfc4Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutPfc5Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutPfc6Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.clIntOutPfc7Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)


    aggregator.assert_all_metrics_covered()

    # --- TEST METADATA ---
    device = {
        'description': 'nvidia-cumulus-linux-switch Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'nvidia-cumulus-linux-switch.device.name',
        'profile': 'nvidia-cumulus-linux-switch',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.40310',
        'vendor': 'nvidia',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
