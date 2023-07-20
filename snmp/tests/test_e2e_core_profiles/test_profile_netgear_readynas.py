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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_netgear_readynas(dd_agent_check):
    config = create_e2e_core_test_config('netgear-readynas')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:netgear-readynas',
        'snmp_host:netgear-readynas.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric(
        'snmp.netgear.nasMgrSoftwareVersion', metric_type=aggregator.GAUGE, tags=common_tags
    )  # FAILING
    tag_rows = [
        [
            'netgear_disk_id:their but their zombies driving forward kept Jaded',
            'netgear_disk_interface:but forward their but zombies driving',
            'netgear_disk_model:Jaded zombies',
            'netgear_disk_serial:acted oxen but oxen',
            'netgear_disk_slot_name:kept kept driving oxen oxen but driving zombies',
        ],
        [
            'netgear_disk_id:zombies driving kept quaintly zombies',
            'netgear_disk_interface:their forward oxen forward',
            'netgear_disk_model:but kept quaintly zombies kept Jaded but Jaded',
            'netgear_disk_serial:forward forward acted oxen acted quaintly',
            'netgear_disk_slot_name:their kept acted forward',
        ],
        [
            'netgear_disk_id:zombies driving kept quaintly zombies',
            'netgear_disk_interface:their forward oxen forward',
            'netgear_disk_model:but kept quaintly zombies kept Jaded but Jaded',
            'netgear_disk_serial:forward forward acted oxen acted quaintly',
            'netgear_disk_slot_name:their kept acted forward',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netgear.ataError', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.netgear.diskCapacity', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )  # FAILING
        aggregator.assert_metric(
            'snmp.netgear.diskTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netgear_fan_type:Jaded Jaded driving kept their forward Jaded kept'],
        ['netgear_fan_type:quaintly their zombies forward but acted zombies oxen'],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netgear.fanRPM', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.netgear.fanStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )  # FAILING

    tag_rows = [
        [
            'netgear_temperature_type:forward Jaded quaintly Jaded acted their',
        ],
        [
            'netgear_temperature_type:forward Jaded quaintly Jaded acted their',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netgear.temperatureMax', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.temperatureMin', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.temperatureValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )  # FAILING

    tag_rows = [
        ['netgear_volume_name:acted Jaded zombies but quaintly their'],
        ['netgear_volume_name:but acted'],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netgear.volumeFreeSpace', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.volumeRAIDLevel', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )  # FAILING
        aggregator.assert_metric('snmp.netgear.volumeSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['netgear_psu_desc:but forward', 'netgear_psu_status:but but oxen forward acted oxen acted quaintly'],
        ['netgear_psu_desc:quaintly their Jaded quaintly Jaded', 'netgear_psu_status:but zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netgear.psu', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'netgear-readynas Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'netgear-readynas.device.name',
        'profile': 'netgear-readynas',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.4526.100.12.1',
        'vendor': 'netgear',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
