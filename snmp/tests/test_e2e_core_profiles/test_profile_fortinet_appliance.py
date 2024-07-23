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
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_fortinet_appliance(dd_agent_check):
    profile = 'fortinet-appliance'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:fortinet-appliance',
        'snmp_host:fortinet.appliance.example',
        'device_hostname:fortinet.appliance.example',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fmHaClusterId', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fmHaPeerNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fmLogRate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fmRaidDiskNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fmRaidSize', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fmSysCpuUsageExcludedNice', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fmSysDiskCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.fmSysDiskUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_row = [
        'fm_device_ent_adom:forward zombies',
        'fm_device_ent_config_state:in-sync',
        'fm_device_ent_connect_state:down',
        'fm_device_ent_db_state:unknown',
        'fm_device_ent_desc:quaintly but kept',
        'fm_device_ent_ha_group:but oxen their Jaded quaintly zombies zombies acted their',
        'fm_device_ent_ha_mode:a-a',
        'fm_device_ent_ip:Jaded acted Jaded',
        'fm_device_ent_mode:faz',
        'fm_device_ent_name:Jaded Jaded their but oxen their driving but',
        'fm_device_ent_sn:quaintly but',
        'fm_device_ent_state:unknown',
        'fm_device_ent_support_state:expired',
    ]

    aggregator.assert_metric('snmp.fmDevice', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [['fm_raid_disk_ent_state:ok'], ['fm_raid_disk_ent_state:spare']]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fmRaidDiskEntSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_row = [
        'fm_ha_peer_ent_enabled:disabled',
        'fm_ha_peer_ent_host_name:their Jaded quaintly kept but',
        'fm_ha_peer_ent_ip:zombies acted oxen Jaded',
        'fm_ha_peer_ent_sn:Jaded',
        'fm_ha_peer_ent_state:down',
    ]
    aggregator.assert_metric('snmp.fmHaPeer', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'Fortinet Appliance dummy device',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'fortinet.appliance.example',
        'profile': 'fortinet-appliance',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.12356.103.1.999',
        'vendor': 'fortinet',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
