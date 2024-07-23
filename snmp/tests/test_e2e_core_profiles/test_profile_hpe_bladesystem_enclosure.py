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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_hpe_bladesystem_enclosure(dd_agent_check):
    profile = 'hpe-bladesystem-enclosure'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:hpe-bladesystem-enclosure',
        'snmp_host:hpe-bladesystem-enclosure.device.name',
        'device_hostname:hpe-bladesystem-enclosure.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'cpq_rack_common_enclosure_temp_condition:ok',
            'cpq_rack_common_enclosure_temp_location:acted oxen but forward kept',
            'cpq_rack_common_enclosure_temp_sensor_enclosure_name:but acted Jaded forward Jaded Jaded forward',
            'cpq_rack_common_enclosure_temp_type:other',
        ],
        [
            'cpq_rack_common_enclosure_temp_condition:other',
            'cpq_rack_common_enclosure_temp_location:kept their quaintly Jaded oxen acted oxen oxen',
            'cpq_rack_common_enclosure_temp_sensor_enclosure_name:Jaded but acted oxen but oxen driving forward their',
            'cpq_rack_common_enclosure_temp_type:caution',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqRackCommonEnclosureTempCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cpq_rack_common_enclosure_fan_condition:failed',
            'cpq_rack_common_enclosure_fan_enclosure_serial_num:oxen quaintly driving',
            'cpq_rack_common_enclosure_fan_location:quaintly quaintly forward',
            'cpq_rack_common_enclosure_fan_part_number:Jaded quaintly oxen Jaded driving kept acted kept',
            'cpq_rack_common_enclosure_fan_present:other',
            'cpq_rack_common_enclosure_fan_redundant:not_redundant',
            'cpq_rack_common_enclosure_fan_redundant_group_id:30',
            'cpq_rack_common_enclosure_fan_spare_part_number:but kept kept their kept Jaded',
        ],
        [
            'cpq_rack_common_enclosure_fan_condition:other',
            'cpq_rack_common_enclosure_fan_enclosure_serial_num:zombies Jaded forward driving oxen',
            'cpq_rack_common_enclosure_fan_location:forward but forward acted kept acted kept quaintly',
            'cpq_rack_common_enclosure_fan_part_number:forward driving driving oxen acted but',
            'cpq_rack_common_enclosure_fan_present:other',
            'cpq_rack_common_enclosure_fan_redundant:redundant',
            'cpq_rack_common_enclosure_fan_redundant_group_id:25',
            'cpq_rack_common_enclosure_fan_spare_part_number:quaintly zombies acted quaintly but quaintly driving',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqRackCommonEnclosureFan', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cpq_rack_common_enclosure_fuse_condition:failed',
            'cpq_rack_common_enclosure_fuse_enclosure_name:zombies but kept',
            'cpq_rack_common_enclosure_fuse_location:but',
            'cpq_rack_common_enclosure_fuse_present:other',
        ],
        [
            'cpq_rack_common_enclosure_fuse_condition:ok',
            'cpq_rack_common_enclosure_fuse_enclosure_name:acted',
            'cpq_rack_common_enclosure_fuse_location:forward quaintly kept their oxen zombies but Jaded kept',
            'cpq_rack_common_enclosure_fuse_present:other',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqRackCommonEnclosureFuse', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cpq_rack_common_enclosure_manager_condition:other',
            'cpq_rack_common_enclosure_manager_enclosure_name:kept but their Jaded their driving forward Jaded',
            'cpq_rack_common_enclosure_manager_location:their driving forward driving acted zombies kept',
            'cpq_rack_common_enclosure_manager_part_number:Jaded quaintly acted acted',
            'cpq_rack_common_enclosure_manager_present:absent',
            'cpq_rack_common_enclosure_manager_redundant:other',
            'cpq_rack_common_enclosure_manager_role:active',
            'cpq_rack_common_enclosure_manager_serial_num:but zombies kept kept kept',
            'cpq_rack_common_enclosure_manager_spare_part_number:kept their but their',
        ],
        [
            'cpq_rack_common_enclosure_manager_condition:other',
            'cpq_rack_common_enclosure_manager_enclosure_name:their but',
            'cpq_rack_common_enclosure_manager_location:acted Jaded their forward their their quaintly',
            'cpq_rack_common_enclosure_manager_part_number:oxen quaintly oxen oxen but oxen',
            'cpq_rack_common_enclosure_manager_present:other',
            'cpq_rack_common_enclosure_manager_redundant:redundant',
            'cpq_rack_common_enclosure_manager_role:active',
            'cpq_rack_common_enclosure_manager_serial_num:but forward Jaded but acted oxen Jaded',
            'cpq_rack_common_enclosure_manager_spare_part_number:driving',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqRackCommonEnclosureManager', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cpq_rack_power_enclosure_blade_autopoweron:enabled',
            'cpq_rack_power_enclosure_condition:ok',
            'cpq_rack_power_enclosure_input_pwr_type:direct_current',
            'cpq_rack_power_enclosure_load_balanced:other',
            'cpq_rack_power_enclosure_mgmt_board_serial_num:kept acted Jaded',
            'cpq_rack_power_enclosure_name:kept acted forward',
            'cpq_rack_power_enclosure_redundant:other',
        ],
        [
            'cpq_rack_power_enclosure_blade_autopoweron:enabled',
            'cpq_rack_power_enclosure_condition:other',
            'cpq_rack_power_enclosure_input_pwr_type:direct_current',
            'cpq_rack_power_enclosure_load_balanced:load_balanced',
            'cpq_rack_power_enclosure_mgmt_board_serial_num:kept quaintly driving',
            'cpq_rack_power_enclosure_name:driving but kept forward oxen acted but forward Jaded',
            'cpq_rack_power_enclosure_redundant:not_redundant',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpqRackPowerEnclosure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'cpq_rack_server_blade_has_fuses:false',
            'cpq_rack_server_blade_name:kept driving Jaded',
            'cpq_rack_server_blade_part_number:their forward kept acted but oxen quaintly',
            'cpq_rack_server_blade_position:1',
            'cpq_rack_server_blade_post_status:completed',
            'cpq_rack_server_blade_powered:other',
            'cpq_rack_server_blade_present:absent',
            'cpq_rack_server_blade_product_id:Jaded zombies acted quaintly',
            'cpq_rack_server_blade_serial_num:kept driving their forward oxen forward but',
            'cpq_rack_server_blade_spare_part_number:zombies acted but forward oxen kept',
            'cpq_rack_server_blade_status:ok',
            'cpq_rack_server_blade_uid:forward',
            'cpq_rack_server_blade_uid_state:led_off',
        ],
        [
            'cpq_rack_server_blade_has_fuses:false',
            'cpq_rack_server_blade_name:their oxen zombies quaintly acted forward',
            'cpq_rack_server_blade_part_number:quaintly but acted driving zombies but',
            'cpq_rack_server_blade_position:13',
            'cpq_rack_server_blade_post_status:started',
            'cpq_rack_server_blade_powered:on',
            'cpq_rack_server_blade_present:absent',
            'cpq_rack_server_blade_product_id:their',
            'cpq_rack_server_blade_serial_num:zombies quaintly kept acted driving oxen oxen but',
            'cpq_rack_server_blade_spare_part_number:forward',
            'cpq_rack_server_blade_status:other',
            'cpq_rack_server_blade_uid:acted but but but acted Jaded kept',
            'cpq_rack_server_blade_uid_state:led_on',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqRackServerBladeFaultMajor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cpqRackServerBladeFaultMinor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cpq_rack_server_temp_sensor_condition:ok',
            'cpq_rack_server_temp_sensor_location:but acted their quaintly kept',
            'cpq_rack_server_temp_sensor_name:forward their their',
            'cpq_rack_server_temp_sensor_type:blowout',
        ],
        [
            'cpq_rack_server_temp_sensor_condition:ok',
            'cpq_rack_server_temp_sensor_location:quaintly quaintly zombies',
            'cpq_rack_server_temp_sensor_name:acted',
            'cpq_rack_server_temp_sensor_type:other',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqRackServerTempSensorCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cpq_rack_power_supply_condition:degraded',
            'cpq_rack_power_supply_enclosure_name:acted kept zombies but acted driving',
            'cpq_rack_power_supply_enclosure_serial_num:acted but zombies zombies acted forward acted',
            'cpq_rack_power_supply_fw_rev:quaintly acted kept',
            'cpq_rack_power_supply_input_line_status:no_error',
            'cpq_rack_power_supply_max_pwr_output:18',
            'cpq_rack_power_supply_part_number:Jaded driving oxen',
            'cpq_rack_power_supply_present:present',
            'cpq_rack_power_supply_serial_num:forward',
            'cpq_rack_power_supply_spare_part_number:kept acted forward quaintly but forward acted forward kept',
            'cpq_rack_power_supply_status:voltage_channel_failed',
        ],
        [
            'cpq_rack_power_supply_condition:degraded',
            'cpq_rack_power_supply_enclosure_name:quaintly driving oxen acted but',
            'cpq_rack_power_supply_enclosure_serial_num:zombies but their acted Jaded but kept driving',
            'cpq_rack_power_supply_fw_rev:driving quaintly acted zombies forward forward',
            'cpq_rack_power_supply_input_line_status:no_error',
            'cpq_rack_power_supply_max_pwr_output:16',
            'cpq_rack_power_supply_part_number:but acted zombies forward',
            'cpq_rack_power_supply_present:other',
            'cpq_rack_power_supply_serial_num:kept oxen zombies acted driving',
            'cpq_rack_power_supply_spare_part_number:their zombies kept forward their oxen quaintly forward',
            'cpq_rack_power_supply_status:dac_failed',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqRackPowerSupplyCurPwrOutput', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cpqRackPowerSupplyExhaustTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cpqRackPowerSupplyIntakeTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'hpe-bladesystem-enclosure Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'hpe-bladesystem-enclosure.device.name',
        'os_name': 'quaintly quaintly Jaded forward oxen kept kept',
        'os_version': 'zombies oxen forward driving kept',
        'profile': 'hpe-bladesystem-enclosure',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.11.5.7.1.2',
        'vendor': 'hp',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
