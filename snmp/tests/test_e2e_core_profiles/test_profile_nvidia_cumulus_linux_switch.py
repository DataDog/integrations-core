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
    assert_extend_generic_entity_sensor,
    assert_extend_generic_if,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_nvidia_cumulus_linux_switch(dd_agent_check):
    profile = 'nvidia-cumulus-linux-switch'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:nvidia-cumulus-linux-switch',
        'snmp_host:nvidia-cumulus-linux-switch.device.name',
        'device_hostname:nvidia-cumulus-linux-switch.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)
    assert_extend_generic_entity_sensor(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cumulus.egressAclCurrentCounters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.egressAclCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.egressAclCurrentMeters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.egressAclCurrentSlices', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.egressAclMaxCounters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.egressAclMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.egressAclMaxMeters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.egressAclMaxSlices', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.ingressAclCurrentCounters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.ingressAclCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.ingressAclCurrentMeters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.ingressAclCurrentSlices', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.ingressAclMaxCounters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.ingressAclMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.ingressAclMaxMeters', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.ingressAclMaxSlices', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.l2MacTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.l2MacTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.cumulus.l3EcmpNextHopTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.cumulus.l3EcmpNextHopTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.cumulus.l3HostTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.l3HostTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.cumulus.l3NextHopTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.cumulus.l3NextHopTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.cumulus.l3RoutingTableCurrentEntries', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.cumulus.l3RoutingTableMaxEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.poeLastUpdateTime', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.poeTotalAvailablePower', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.poeTotalSystemPower', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cumulus.poeTotalUsedPower', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['cumulus_cl_port_name:their zombies'],
        ['cumulus_cl_port_name:zombies zombies acted oxen but oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cumulus.clBufferOverflowDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clEgressNonQDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clEgressQOverflowDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clL3AclDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clL3v4InDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['cumulus_cl_int_port_name:forward but'],
        ['cumulus_cl_int_port_name:oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cumulus.clIntInBcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntInMcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.cumulus.clIntInOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cumulus.clIntInUcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutBcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutMcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutUcastPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['cumulus_cl_int_pfc_port_name:driving Jaded driving Jaded kept oxen driving quaintly'],
        ['cumulus_cl_int_pfc_port_name:forward kept quaintly quaintly driving oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cumulus.clIntInPausePkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntInPfc0Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntInPfc1Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntInPfc2Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntInPfc3Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntInPfc4Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntInPfc5Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntInPfc6Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntInPfc7Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutPausePkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutPfc0Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutPfc1Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutPfc2Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutPfc3Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutPfc4Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutPfc5Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutPfc6Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cumulus.clIntOutPfc7Pkt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

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
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
