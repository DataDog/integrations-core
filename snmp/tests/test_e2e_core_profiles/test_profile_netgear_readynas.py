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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_netgear_readynas(dd_agent_check):
    profile = 'netgear-readynas'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:netgear-readynas',
        'snmp_host:netgear-readynas.device.name',
        'device_hostname:netgear-readynas.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'netgear_readynasos_disk_id:acted forward forward Jaded',
            'netgear_readynasos_disk_interface:kept zombies acted quaintly',
            'netgear_readynasos_disk_model:acted but driving',
            'netgear_readynasos_disk_serial:their quaintly zombies acted zombies',
            'netgear_readynasos_disk_slot_name:their oxen forward Jaded but',
            'netgear_readynasos_disk_state:online',
        ],
        [
            'netgear_readynasos_disk_id:but kept',
            'netgear_readynasos_disk_interface:Jaded kept forward oxen driving kept acted zombies',
            'netgear_readynasos_disk_model:kept their',
            'netgear_readynasos_disk_serial:but driving their driving acted driving zombies their Jaded',
            'netgear_readynasos_disk_slot_name:acted',
            'netgear_readynasos_disk_state:offline',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netgear.readynasos.ataError', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.readynasos.diskCapacity', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.readynasos.diskTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netgear_readynasos_fan_type:but oxen oxen acted forward Jaded kept Jaded Jaded'],
        ['netgear_readynasos_fan_type:forward zombies Jaded but zombies forward zombies zombies forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netgear.readynasos.fanRPM', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.readynasos.fanStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netgear_readynasos_temperature_type:driving driving quaintly'],
        ['netgear_readynasos_temperature_type:their but zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netgear.readynasos.temperatureMax', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.readynasos.temperatureMin', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.readynasos.temperatureValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netgear_readynasos_volume_name:quaintly', 'netgear_readynasos_volume_status:redundant'],
        [
            'netgear_readynasos_volume_name:zombies kept Jaded Jaded kept Jaded acted their',
            'netgear_readynasos_volume_status:unknown',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netgear.readynasos.volumeRAIDLevel', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.readynasos.volumeFreeSpace', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.readynasos.volumeSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netgear.readynasos.volumeRAIDLevel', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netgear_readynasos_psu_desc:Jaded forward but kept quaintly their but',
            'netgear_readynasos_psu_status:quaintly zombies but zombies forward Jaded forward',
        ],
        [
            'netgear_readynasos_psu_desc:their acted Jaded oxen driving Jaded forward zombies',
            'netgear_readynasos_psu_status:quaintly their acted kept zombies driving',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netgear.readynasos.psu', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'netgear-readynas Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'netgear-readynas.device.name',
        'profile': 'netgear-readynas',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.4526.100.16.1',
        'vendor': 'netgear',
        'device_type': 'storage',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
