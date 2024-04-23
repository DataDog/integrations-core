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


def test_e2e_profile_cisco_ucs(dd_agent_check):
    profile = 'cisco-ucs'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-ucs',
        'snmp_host:cisco-ucs.device.name',
        'device_hostname:cisco-ucs.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'cucs_compute_board_dn:acted but kept acted acted zombies oxen',
            'cucs_compute_board_model:acted kept forward forward their',
            'cucs_compute_board_oper_power:power_save',
            'cucs_compute_board_oper_state:identity_unestablishable',
            'cucs_compute_board_operability:degraded',
            'cucs_compute_board_perf:upper_non_recoverable',
            'cucs_compute_board_power:offline',
            'cucs_compute_board_presence:equipped_with_malformed_fru',
            'cucs_compute_board_serial:their zombies their forward oxen forward oxen acted',
            'cucs_compute_board_thermal:lower_critical',
            'cucs_compute_board_vendor:zombies quaintly driving kept',
            'cucs_compute_board_voltage:upper_non_recoverable',
        ],
        [
            'cucs_compute_board_dn:acted their but zombies oxen forward kept acted Jaded',
            'cucs_compute_board_model:but Jaded oxen quaintly but acted kept driving',
            'cucs_compute_board_oper_power:test',
            'cucs_compute_board_oper_state:performance_problem',
            'cucs_compute_board_operability:accessibility_problem',
            'cucs_compute_board_perf:upper_non_critical',
            'cucs_compute_board_power:online',
            'cucs_compute_board_presence:equipped_with_malformed_fru',
            'cucs_compute_board_serial:Jaded quaintly but quaintly forward quaintly their',
            'cucs_compute_board_thermal:upper_non_recoverable',
            'cucs_compute_board_vendor:acted quaintly Jaded quaintly forward zombies their but',
            'cucs_compute_board_voltage:lower_non_critical',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cucsComputeBoard', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['cucs_compute_mb_power_stats_dn:forward their'],
        ['cucs_compute_mb_power_stats_dn:kept their zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsComputeMbPowerStatsConsumedPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cucsComputeMbPowerStatsInputCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cucsComputeMbPowerStatsInputVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['mem:28682'],
        ['mem:33619'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'cucs_compute_rack_unit_admin_power:admin_up',
            'cucs_compute_rack_unit_admin_state:out_of_service',
            'cucs_compute_rack_unit_association:removing',
            'cucs_compute_rack_unit_availability:unavailable',
            'cucs_compute_rack_unit_check_point:discovered',
            'cucs_compute_rack_unit_dn:zombies zombies quaintly Jaded Jaded kept kept oxen driving',
            'cucs_compute_rack_unit_model:their Jaded but oxen forward their forward Jaded',
            'cucs_compute_rack_unit_name:but kept their acted their their Jaded kept',
            'cucs_compute_rack_unit_num_of_cores:1392027044',
            'cucs_compute_rack_unit_num_of_cpus:3337463896',
            'cucs_compute_rack_unit_num_of_threads:431335899',
            'cucs_compute_rack_unit_oper_power:test',
            'cucs_compute_rack_unit_oper_state:unassociated',
            'cucs_compute_rack_unit_operability:degraded',
            'cucs_compute_rack_unit_presence:equipped_identity_unestablishable',
            'cucs_compute_rack_unit_serial:but oxen Jaded driving',
            'cucs_compute_rack_unit_uuid:driving acted forward acted oxen forward their but acted',
            'cucs_compute_rack_unit_vendor:acted quaintly zombies their Jaded Jaded',
        ],
        [
            'cucs_compute_rack_unit_admin_power:cycle_wait',
            'cucs_compute_rack_unit_admin_state:in_maintenance',
            'cucs_compute_rack_unit_association:removing',
            'cucs_compute_rack_unit_availability:available',
            'cucs_compute_rack_unit_check_point:removing',
            'cucs_compute_rack_unit_dn:quaintly',
            'cucs_compute_rack_unit_model:zombies driving zombies quaintly oxen forward',
            'cucs_compute_rack_unit_name:oxen oxen quaintly zombies Jaded but but',
            'cucs_compute_rack_unit_num_of_cores:3097236775',
            'cucs_compute_rack_unit_num_of_cpus:128161696',
            'cucs_compute_rack_unit_num_of_threads:78797133',
            'cucs_compute_rack_unit_oper_power:ok',
            'cucs_compute_rack_unit_oper_state:power_off',
            'cucs_compute_rack_unit_operability:identity_unestablishable',
            'cucs_compute_rack_unit_presence:inaccessible',
            'cucs_compute_rack_unit_serial:driving',
            'cucs_compute_rack_unit_uuid:zombies oxen',
            'cucs_compute_rack_unit_vendor:kept their Jaded acted driving Jaded but quaintly',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsComputeRackUnitAvailableMemory', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cucsComputeRackUnitTotalMemory', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['cucs_compute_rack_unit_mb_temp_stats_dn:oxen forward zombies forward their acted quaintly kept'],
        ['cucs_compute_rack_unit_mb_temp_stats_dn:their zombies Jaded forward oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsComputeRackUnitMbTempStatsAmbientTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cucsComputeRackUnitMbTempStatsFrontTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cucsComputeRackUnitMbTempStatsIoh1Temp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cucsComputeRackUnitMbTempStatsRearTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cucs_equipment_fan_dn:driving but',
            'cucs_equipment_fan_int_type:switch',
            'cucs_equipment_fan_oper_state:performance_problem',
            'cucs_equipment_fan_operability:degraded',
            'cucs_equipment_fan_perf:upper_critical',
            'cucs_equipment_fan_power:unknown',
            'cucs_equipment_fan_presence:equipped_with_malformed_fru',
        ],
        [
            'cucs_equipment_fan_dn:forward',
            'cucs_equipment_fan_int_type:switch',
            'cucs_equipment_fan_oper_state:chassis_intrusion',
            'cucs_equipment_fan_operability:accessibility_problem',
            'cucs_equipment_fan_perf:ok',
            'cucs_equipment_fan_power:unknown',
            'cucs_equipment_fan_presence:mismatch_identity_unestablishable',
        ],
        [
            'cucs_equipment_fan_dn:oxen driving Jaded driving kept driving quaintly',
            'cucs_equipment_fan_int_type:switch',
            'cucs_equipment_fan_oper_state:unknown',
            'cucs_equipment_fan_operability:operable',
            'cucs_equipment_fan_perf:unknown',
            'cucs_equipment_fan_power:error',
            'cucs_equipment_fan_presence:mismatch',
        ],
        [
            'cucs_equipment_fan_dn:their but quaintly',
            'cucs_equipment_fan_int_type:switch',
            'cucs_equipment_fan_oper_state:removed',
            'cucs_equipment_fan_operability:powered_off',
            'cucs_equipment_fan_perf:lower_non_critical',
            'cucs_equipment_fan_power:offline',
            'cucs_equipment_fan_presence:unknown',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cucsEquipmentFan', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'cucs_equipment_psu_dn:Jaded oxen zombies',
            'cucs_equipment_psu_model:zombies their',
            'cucs_equipment_psu_oper_state:identity_unestablishable',
            'cucs_equipment_psu_operability:chassis_intrusion',
            'cucs_equipment_psu_perf:upper_non_critical',
            'cucs_equipment_psu_power:offline',
            'cucs_equipment_psu_presence:equipped_identity_unestablishable',
            'cucs_equipment_psu_revision:their driving zombies but driving kept',
            'cucs_equipment_psu_serial:acted but their forward forward zombies but',
        ],
        [
            'cucs_equipment_psu_dn:forward quaintly',
            'cucs_equipment_psu_model:acted but',
            'cucs_equipment_psu_oper_state:performance_problem',
            'cucs_equipment_psu_operability:inoperable',
            'cucs_equipment_psu_perf:upper_critical',
            'cucs_equipment_psu_power:off',
            'cucs_equipment_psu_presence:mismatch_slave',
            'cucs_equipment_psu_revision:quaintly Jaded kept kept forward',
            'cucs_equipment_psu_serial:quaintly quaintly but acted acted',
        ],
        [
            'cucs_equipment_psu_dn:kept Jaded zombies',
            'cucs_equipment_psu_model:zombies quaintly acted',
            'cucs_equipment_psu_oper_state:backplane_port_problem',
            'cucs_equipment_psu_operability:backplane_port_problem',
            'cucs_equipment_psu_perf:lower_critical',
            'cucs_equipment_psu_power:offduty',
            'cucs_equipment_psu_presence:inaccessible',
            'cucs_equipment_psu_revision:acted forward driving quaintly forward driving quaintly',
            'cucs_equipment_psu_serial:forward their forward acted kept oxen',
        ],
        [
            'cucs_equipment_psu_dn:their kept Jaded acted their oxen',
            'cucs_equipment_psu_model:driving quaintly kept but their',
            'cucs_equipment_psu_oper_state:power_problem',
            'cucs_equipment_psu_operability:power_problem',
            'cucs_equipment_psu_perf:lower_non_critical',
            'cucs_equipment_psu_power:on',
            'cucs_equipment_psu_presence:unknown',
            'cucs_equipment_psu_revision:oxen oxen',
            'cucs_equipment_psu_serial:zombies acted Jaded acted but their oxen Jaded Jaded',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cucsEquipmentPsu', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'cucs_equipment_health_led_color:amber',
            'cucs_equipment_health_led_dn:but kept driving forward kept quaintly but their driving',
            'cucs_equipment_health_led_oper_state:eth',
            'cucs_equipment_health_led_state:critical',
        ],
        [
            'cucs_equipment_health_led_color:amber',
            'cucs_equipment_health_led_dn:quaintly oxen zombies forward',
            'cucs_equipment_health_led_oper_state:fc',
            'cucs_equipment_health_led_state:critical',
        ],
        [
            'cucs_equipment_health_led_color:blue',
            'cucs_equipment_health_led_dn:driving acted but oxen Jaded but quaintly',
            'cucs_equipment_health_led_oper_state:eth',
            'cucs_equipment_health_led_state:critical',
        ],
        [
            'cucs_equipment_health_led_color:red',
            'cucs_equipment_health_led_dn:kept zombies acted kept acted Jaded',
            'cucs_equipment_health_led_oper_state:on',
            'cucs_equipment_health_led_state:normal',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsEquipmentHealthLed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cucs_memory_unit_dn:driving Jaded',
            'cucs_memory_unit_location:oxen oxen but Jaded kept forward',
            'cucs_memory_unit_oper_state:accessibility_problem',
            'cucs_memory_unit_operability:degraded',
            'cucs_memory_unit_perf:upper_non_recoverable',
            'cucs_memory_unit_power:ok',
            'cucs_memory_unit_presence:inaccessible',
            'cucs_memory_unit_type:rom',
        ],
        [
            'cucs_memory_unit_dn:driving oxen but their oxen',
            'cucs_memory_unit_location:driving but zombies',
            'cucs_memory_unit_oper_state:performance_problem',
            'cucs_memory_unit_operability:identity_unestablishable',
            'cucs_memory_unit_perf:upper_non_recoverable',
            'cucs_memory_unit_power:ok',
            'cucs_memory_unit_presence:unknown',
            'cucs_memory_unit_type:other',
        ],
        [
            'cucs_memory_unit_dn:forward kept oxen acted quaintly forward driving',
            'cucs_memory_unit_location:Jaded forward acted zombies kept their Jaded acted quaintly',
            'cucs_memory_unit_oper_state:chassis_intrusion',
            'cucs_memory_unit_operability:malformed_fru',
            'cucs_memory_unit_perf:lower_non_recoverable',
            'cucs_memory_unit_power:offduty',
            'cucs_memory_unit_presence:missing_slave',
            'cucs_memory_unit_type:rom',
        ],
        [
            'cucs_memory_unit_dn:zombies but acted but forward',
            'cucs_memory_unit_location:kept quaintly driving',
            'cucs_memory_unit_oper_state:accessibility_problem',
            'cucs_memory_unit_operability:disabled',
            'cucs_memory_unit_perf:upper_non_recoverable',
            'cucs_memory_unit_power:error',
            'cucs_memory_unit_presence:equipped_slave',
            'cucs_memory_unit_type:sdram',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsMemoryUnitCapacity', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['cucs_memory_unit_env_stats_dn:Jaded kept oxen oxen Jaded but zombies'],
        ['cucs_memory_unit_env_stats_dn:but quaintly kept acted'],
        ['cucs_memory_unit_env_stats_dn:quaintly but Jaded driving zombies driving'],
        ['cucs_memory_unit_env_stats_dn:their acted oxen quaintly zombies but acted'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsMemoryUnitEnvStatsTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['cucs_processor_env_stats_dn:acted forward kept forward'],
        ['cucs_processor_env_stats_dn:their zombies their Jaded'],
        ['cucs_processor_env_stats_dn:zombies but oxen'],
        ['cucs_processor_env_stats_dn:zombies zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsProcessorEnvStatsTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cucs_processor_unit_arch:any',
            'cucs_processor_unit_cores:3053647418',
            'cucs_processor_unit_cores_enabled:2907098472',
            'cucs_processor_unit_dn:acted Jaded Jaded',
            'cucs_processor_unit_model:kept driving quaintly driving their quaintly Jaded kept zombies',
            'cucs_processor_unit_oper_state:power_problem',
            'cucs_processor_unit_operability:power_problem',
            'cucs_processor_unit_perf:upper_non_recoverable',
            'cucs_processor_unit_power:offduty',
            'cucs_processor_unit_presence:equipped_slave',
            'cucs_processor_unit_threads:1959738939',
            'cucs_processor_unit_vendor:quaintly zombies quaintly oxen zombies',
        ],
        [
            'cucs_processor_unit_arch:any',
            'cucs_processor_unit_cores:4045456538',
            'cucs_processor_unit_cores_enabled:81819481',
            'cucs_processor_unit_dn:but',
            'cucs_processor_unit_model:Jaded but driving zombies oxen Jaded Jaded quaintly but',
            'cucs_processor_unit_oper_state:voltage_problem',
            'cucs_processor_unit_operability:voltage_problem',
            'cucs_processor_unit_perf:upper_critical',
            'cucs_processor_unit_power:offline',
            'cucs_processor_unit_presence:equipped_with_malformed_fru',
            'cucs_processor_unit_threads:948464931',
            'cucs_processor_unit_vendor:quaintly forward',
        ],
        [
            'cucs_processor_unit_arch:intel_p4c',
            'cucs_processor_unit_cores:3089744816',
            'cucs_processor_unit_cores_enabled:50511177',
            'cucs_processor_unit_dn:kept driving',
            'cucs_processor_unit_model:Jaded their acted acted zombies',
            'cucs_processor_unit_oper_state:identity_unestablishable',
            'cucs_processor_unit_operability:backplane_port_problem',
            'cucs_processor_unit_perf:upper_non_critical',
            'cucs_processor_unit_power:offline',
            'cucs_processor_unit_presence:equipped_slave',
            'cucs_processor_unit_threads:3873199318',
            'cucs_processor_unit_vendor:driving but their driving their driving forward forward',
        ],
        [
            'cucs_processor_unit_arch:intel_p4c',
            'cucs_processor_unit_cores:861697837',
            'cucs_processor_unit_cores_enabled:3562772907',
            'cucs_processor_unit_dn:forward their Jaded forward kept zombies',
            'cucs_processor_unit_model:quaintly but oxen acted Jaded oxen',
            'cucs_processor_unit_oper_state:chassis_intrusion',
            'cucs_processor_unit_operability:chassis_intrusion',
            'cucs_processor_unit_perf:upper_non_recoverable',
            'cucs_processor_unit_power:ok',
            'cucs_processor_unit_presence:empty',
            'cucs_processor_unit_threads:3156049979',
            'cucs_processor_unit_vendor:zombies',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cucsProcessorUnit', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_health_na',
            'cucs_storage_flex_flash_card_card_state:failed',
            'cucs_storage_flex_flash_card_card_sync:auto',
            'cucs_storage_flex_flash_card_connection_protocol:unspecified',
            'cucs_storage_flex_flash_card_dn:quaintly',
            'cucs_storage_flex_flash_card_drives_enabled:quaintly Jaded but Jaded but oxen acted their',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_primary',
            'cucs_storage_flex_flash_card_operability:bios_post_timeout',
            'cucs_storage_flex_flash_card_presence:equipped_slave',
            'cucs_storage_flex_flash_card_revision:forward kept acted acted Jaded oxen oxen forward',
            'cucs_storage_flex_flash_card_serial:their their their acted but but',
            'cucs_storage_flex_flash_card_card_type:their',
        ],
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_health_na',
            'cucs_storage_flex_flash_card_card_state:ignored',
            'cucs_storage_flex_flash_card_card_sync:auto',
            'cucs_storage_flex_flash_card_connection_protocol:sas',
            'cucs_storage_flex_flash_card_dn:kept but acted their Jaded oxen driving zombies their',
            'cucs_storage_flex_flash_card_drives_enabled:forward quaintly but oxen their',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_secondary_unhealthy',
            'cucs_storage_flex_flash_card_operability:powered_off',
            'cucs_storage_flex_flash_card_presence:mismatch_slave',
            'cucs_storage_flex_flash_card_revision:driving Jaded zombies their quaintly their their',
            'cucs_storage_flex_flash_card_serial:Jaded driving oxen quaintly zombies but',
            'cucs_storage_flex_flash_card_card_type:oxen zombies acted zombies kept',
        ],
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_health_na',
            'cucs_storage_flex_flash_card_card_state:unknown',
            'cucs_storage_flex_flash_card_card_sync:manual',
            'cucs_storage_flex_flash_card_connection_protocol:nvme',
            'cucs_storage_flex_flash_card_dn:quaintly',
            'cucs_storage_flex_flash_card_drives_enabled:their driving forward quaintly',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_secondary_unhealthy',
            'cucs_storage_flex_flash_card_operability:voltage_problem',
            'cucs_storage_flex_flash_card_presence:equipped_identity_unestablishable',
            'cucs_storage_flex_flash_card_revision:acted their zombies quaintly but',
            'cucs_storage_flex_flash_card_serial:Jaded zombies Jaded zombies but their Jaded quaintly',
            'cucs_storage_flex_flash_card_card_type:driving quaintly forward zombies but',
        ],
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_health_ok',
            'cucs_storage_flex_flash_card_card_state:configured',
            'cucs_storage_flex_flash_card_card_sync:na',
            'cucs_storage_flex_flash_card_connection_protocol:nvme',
            'cucs_storage_flex_flash_card_dn:kept oxen zombies forward their but forward their',
            'cucs_storage_flex_flash_card_drives_enabled:their',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_secondary_unhealthy',
            'cucs_storage_flex_flash_card_operability:removed',
            'cucs_storage_flex_flash_card_presence:equipped_not_primary',
            'cucs_storage_flex_flash_card_revision:quaintly Jaded their forward quaintly but oxen',
            'cucs_storage_flex_flash_card_serial:their',
            'cucs_storage_flex_flash_card_card_type:oxen their',
        ],
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_health_ok',
            'cucs_storage_flex_flash_card_card_state:initializing',
            'cucs_storage_flex_flash_card_card_sync:unknown',
            'cucs_storage_flex_flash_card_connection_protocol:nvme',
            'cucs_storage_flex_flash_card_dn:quaintly Jaded zombies',
            'cucs_storage_flex_flash_card_drives_enabled:their',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_unpaired_primary',
            'cucs_storage_flex_flash_card_operability:power_problem',
            'cucs_storage_flex_flash_card_presence:missing_slave',
            'cucs_storage_flex_flash_card_revision:oxen their acted zombies acted oxen their',
            'cucs_storage_flex_flash_card_serial:quaintly',
            'cucs_storage_flex_flash_card_card_type:forward forward forward their but',
        ],
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_raid_sync_in_progress',
            'cucs_storage_flex_flash_card_card_state:unknown',
            'cucs_storage_flex_flash_card_card_sync:na',
            'cucs_storage_flex_flash_card_connection_protocol:nvme',
            'cucs_storage_flex_flash_card_dn:driving their',
            'cucs_storage_flex_flash_card_drives_enabled:kept Jaded oxen forward',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_unpaired_primary',
            'cucs_storage_flex_flash_card_operability:unknown',
            'cucs_storage_flex_flash_card_presence:empty',
            'cucs_storage_flex_flash_card_revision:Jaded zombies but but but their acted quaintly',
            'cucs_storage_flex_flash_card_serial:acted',
            'cucs_storage_flex_flash_card_card_type:oxen zombies',
        ],
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_unhealthy_other',
            'cucs_storage_flex_flash_card_card_state:ignored',
            'cucs_storage_flex_flash_card_card_sync:auto',
            'cucs_storage_flex_flash_card_connection_protocol:nvme',
            'cucs_storage_flex_flash_card_dn:but oxen oxen',
            'cucs_storage_flex_flash_card_drives_enabled:quaintly quaintly Jaded driving forward Jaded Jaded',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_primary',
            'cucs_storage_flex_flash_card_operability:thermal_problem',
            'cucs_storage_flex_flash_card_presence:equipped_identity_unestablishable',
            'cucs_storage_flex_flash_card_revision:quaintly quaintly kept forward kept their',
            'cucs_storage_flex_flash_card_serial:oxen',
            'cucs_storage_flex_flash_card_card_type:driving but acted driving acted driving',
        ],
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_unhealthy_raid',
            'cucs_storage_flex_flash_card_card_state:configured',
            'cucs_storage_flex_flash_card_card_sync:unknown',
            'cucs_storage_flex_flash_card_connection_protocol:nvme',
            'cucs_storage_flex_flash_card_dn:acted driving oxen kept forward quaintly but kept',
            'cucs_storage_flex_flash_card_drives_enabled:but quaintly driving zombies quaintly kept oxen',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_primary',
            'cucs_storage_flex_flash_card_operability:inoperable',
            'cucs_storage_flex_flash_card_presence:mismatch',
            'cucs_storage_flex_flash_card_revision:quaintly but Jaded their zombies but',
            'cucs_storage_flex_flash_card_serial:their their kept forward acted quaintly',
            'cucs_storage_flex_flash_card_card_type:their acted quaintly quaintly oxen quaintly but kept',
        ],
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_unhealthy_raid',
            'cucs_storage_flex_flash_card_card_state:ignored',
            'cucs_storage_flex_flash_card_card_sync:manual',
            'cucs_storage_flex_flash_card_connection_protocol:sata',
            'cucs_storage_flex_flash_card_dn:quaintly',
            'cucs_storage_flex_flash_card_drives_enabled:acted Jaded quaintly zombies',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_secondary_unhealthy',
            'cucs_storage_flex_flash_card_operability:identity_unestablishable',
            'cucs_storage_flex_flash_card_presence:mismatch',
            'cucs_storage_flex_flash_card_revision:Jaded',
            'cucs_storage_flex_flash_card_serial:forward their their driving zombies driving forward',
            'cucs_storage_flex_flash_card_card_type:quaintly',
        ],
        [
            'cucs_storage_flex_flash_card_card_health:ff_phy_unhealthy_raid',
            'cucs_storage_flex_flash_card_card_state:unknown',
            'cucs_storage_flex_flash_card_card_sync:unknown',
            'cucs_storage_flex_flash_card_connection_protocol:sas',
            'cucs_storage_flex_flash_card_dn:zombies their kept driving Jaded Jaded their acted',
            'cucs_storage_flex_flash_card_drives_enabled:but but driving',
            'cucs_storage_flex_flash_card_mode:ff_phy_drive_primary',
            'cucs_storage_flex_flash_card_operability:unknown',
            'cucs_storage_flex_flash_card_presence:equipped',
            'cucs_storage_flex_flash_card_revision:acted acted but zombies Jaded quaintly',
            'cucs_storage_flex_flash_card_serial:acted driving',
            'cucs_storage_flex_flash_card_card_type:zombies zombies',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsStorageFlexFlashCardReadIOErrorCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cucsStorageFlexFlashCardSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cucsStorageFlexFlashCardWriteIOErrorCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_error_cards_access_error',
            'cucs_storage_flex_flash_controller_controller_state:ffc_usb_disconnected',
            'cucs_storage_flex_flash_controller_dn:zombies acted',
            'cucs_storage_flex_flash_controller_flex_flash_type:unknown',
            'cucs_storage_flex_flash_controller_has_error:no_error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:na',
            'cucs_storage_flex_flash_controller_model:forward quaintly',
            'cucs_storage_flex_flash_controller_oper_state:degraded',
            'cucs_storage_flex_flash_controller_operability:degraded',
            'cucs_storage_flex_flash_controller_operating_mode:util',
            'cucs_storage_flex_flash_controller_perf:unknown',
            'cucs_storage_flex_flash_controller_physical_drive_count:1017665252',
            'cucs_storage_flex_flash_controller_power:on',
            'cucs_storage_flex_flash_controller_presence:equipped_with_malformed_fru',
            'cucs_storage_flex_flash_controller_type:flash',
            'cucs_storage_flex_flash_controller_vendor:Jaded zombies forward but forward',
            'cucs_storage_flex_flash_controller_virtual_drive_count:3388646394',
        ],
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_error_media_write_protected',
            'cucs_storage_flex_flash_controller_controller_state:ffc_usb_disconnected',
            'cucs_storage_flex_flash_controller_dn:acted acted driving zombies acted',
            'cucs_storage_flex_flash_controller_flex_flash_type:astoria',
            'cucs_storage_flex_flash_controller_has_error:error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:no',
            'cucs_storage_flex_flash_controller_model:Jaded quaintly kept acted quaintly zombies driving kept kept',
            'cucs_storage_flex_flash_controller_oper_state:performance_problem',
            'cucs_storage_flex_flash_controller_operability:accessibility_problem',
            'cucs_storage_flex_flash_controller_operating_mode:unknown',
            'cucs_storage_flex_flash_controller_perf:upper_non_recoverable',
            'cucs_storage_flex_flash_controller_physical_drive_count:2260981457',
            'cucs_storage_flex_flash_controller_power:error',
            'cucs_storage_flex_flash_controller_presence:equipped_identity_unestablishable',
            'cucs_storage_flex_flash_controller_type:sas',
            'cucs_storage_flex_flash_controller_vendor:but acted but oxen acted forward',
            'cucs_storage_flex_flash_controller_virtual_drive_count:2448782283',
        ],
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_error_sd247_card_detected',
            'cucs_storage_flex_flash_controller_controller_state:ffc_software_err',
            'cucs_storage_flex_flash_controller_dn:forward kept their',
            'cucs_storage_flex_flash_controller_flex_flash_type:fx3s',
            'cucs_storage_flex_flash_controller_has_error:error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:yes',
            'cucs_storage_flex_flash_controller_model:their',
            'cucs_storage_flex_flash_controller_oper_state:thermal_problem',
            'cucs_storage_flex_flash_controller_operability:chassis_intrusion',
            'cucs_storage_flex_flash_controller_operating_mode:unknown',
            'cucs_storage_flex_flash_controller_perf:upper_non_recoverable',
            'cucs_storage_flex_flash_controller_physical_drive_count:843144129',
            'cucs_storage_flex_flash_controller_power:ok',
            'cucs_storage_flex_flash_controller_presence:equipped_identity_unestablishable',
            'cucs_storage_flex_flash_controller_type:sata',
            'cucs_storage_flex_flash_controller_vendor:acted zombies acted Jaded',
            'cucs_storage_flex_flash_controller_virtual_drive_count:1016878139',
        ],
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_error_secondary_unhealthy_card',
            'cucs_storage_flex_flash_controller_controller_state:ffc_wait_user',
            'cucs_storage_flex_flash_controller_dn:acted kept kept oxen but Jaded zombies',
            'cucs_storage_flex_flash_controller_flex_flash_type:fx3s',
            'cucs_storage_flex_flash_controller_has_error:error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:no',
            'cucs_storage_flex_flash_controller_model:their quaintly but their oxen Jaded zombies their',
            'cucs_storage_flex_flash_controller_oper_state:operable',
            'cucs_storage_flex_flash_controller_operability:removed',
            'cucs_storage_flex_flash_controller_operating_mode:util',
            'cucs_storage_flex_flash_controller_perf:ok',
            'cucs_storage_flex_flash_controller_physical_drive_count:3171059783',
            'cucs_storage_flex_flash_controller_power:offduty',
            'cucs_storage_flex_flash_controller_presence:missing_slave',
            'cucs_storage_flex_flash_controller_type:m2',
            'cucs_storage_flex_flash_controller_vendor:driving acted Jaded driving forward',
            'cucs_storage_flex_flash_controller_virtual_drive_count:3321093574',
        ],
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_flexd_error_im_sd0_sd1_ignored',
            'cucs_storage_flex_flash_controller_controller_state:ffc_rebuilding',
            'cucs_storage_flex_flash_controller_dn:acted kept their their forward',
            'cucs_storage_flex_flash_controller_flex_flash_type:astoria',
            'cucs_storage_flex_flash_controller_has_error:error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:yes',
            'cucs_storage_flex_flash_controller_model:zombies',
            'cucs_storage_flex_flash_controller_oper_state:chassis_intrusion',
            'cucs_storage_flex_flash_controller_operability:identity_unestablishable',
            'cucs_storage_flex_flash_controller_operating_mode:mirror',
            'cucs_storage_flex_flash_controller_perf:unknown',
            'cucs_storage_flex_flash_controller_physical_drive_count:3492040850',
            'cucs_storage_flex_flash_controller_power:power_save',
            'cucs_storage_flex_flash_controller_presence:equipped_identity_unestablishable',
            'cucs_storage_flex_flash_controller_type:sas',
            'cucs_storage_flex_flash_controller_vendor:acted zombies acted zombies',
            'cucs_storage_flex_flash_controller_virtual_drive_count:3974178726',
        ],
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_flexd_error_im_sd_cards_op_mode_mismatch',
            'cucs_storage_flex_flash_controller_controller_state:ffc_usb_connected',
            'cucs_storage_flex_flash_controller_dn:oxen',
            'cucs_storage_flex_flash_controller_flex_flash_type:unknown',
            'cucs_storage_flex_flash_controller_has_error:no_error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:na',
            'cucs_storage_flex_flash_controller_model:oxen kept but oxen acted their driving driving',
            'cucs_storage_flex_flash_controller_oper_state:performance_problem',
            'cucs_storage_flex_flash_controller_operability:performance_problem',
            'cucs_storage_flex_flash_controller_operating_mode:mirror',
            'cucs_storage_flex_flash_controller_perf:ok',
            'cucs_storage_flex_flash_controller_physical_drive_count:3481619645',
            'cucs_storage_flex_flash_controller_power:failed',
            'cucs_storage_flex_flash_controller_presence:equipped_not_primary',
            'cucs_storage_flex_flash_controller_type:nvme',
            'cucs_storage_flex_flash_controller_vendor:forward driving driving oxen quaintly kept Jaded',
            'cucs_storage_flex_flash_controller_virtual_drive_count:3308373507',
        ],
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_flexd_error_im_sd_healthy_sd_un_ignored',
            'cucs_storage_flex_flash_controller_controller_state:ffc_config',
            'cucs_storage_flex_flash_controller_dn:forward driving',
            'cucs_storage_flex_flash_controller_flex_flash_type:astoria',
            'cucs_storage_flex_flash_controller_has_error:no_error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:no',
            'cucs_storage_flex_flash_controller_model:their their',
            'cucs_storage_flex_flash_controller_oper_state:accessibility_problem',
            'cucs_storage_flex_flash_controller_operability:chassis_intrusion',
            'cucs_storage_flex_flash_controller_operating_mode:unknown',
            'cucs_storage_flex_flash_controller_perf:lower_critical',
            'cucs_storage_flex_flash_controller_physical_drive_count:1491658207',
            'cucs_storage_flex_flash_controller_power:error',
            'cucs_storage_flex_flash_controller_presence:equipped_slave',
            'cucs_storage_flex_flash_controller_type:m2',
            'cucs_storage_flex_flash_controller_vendor:acted kept driving but',
            'cucs_storage_flex_flash_controller_virtual_drive_count:4220880751',
        ],
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_flexd_error_sd_card0_healthy_op_mode_mismatch',
            'cucs_storage_flex_flash_controller_controller_state:ffc_init',
            'cucs_storage_flex_flash_controller_dn:their Jaded forward kept',
            'cucs_storage_flex_flash_controller_flex_flash_type:unknown',
            'cucs_storage_flex_flash_controller_has_error:no_error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:na',
            'cucs_storage_flex_flash_controller_model:acted kept acted Jaded driving kept oxen their their',
            'cucs_storage_flex_flash_controller_oper_state:performance_problem',
            'cucs_storage_flex_flash_controller_operability:chassis_intrusion',
            'cucs_storage_flex_flash_controller_operating_mode:util',
            'cucs_storage_flex_flash_controller_perf:lower_critical',
            'cucs_storage_flex_flash_controller_physical_drive_count:2548286795',
            'cucs_storage_flex_flash_controller_power:failed',
            'cucs_storage_flex_flash_controller_presence:inaccessible',
            'cucs_storage_flex_flash_controller_type:external',
            'cucs_storage_flex_flash_controller_vendor:but',
            'cucs_storage_flex_flash_controller_virtual_drive_count:2404675796',
        ],
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_flexd_error_sd_card_op_mode_mismatch',
            'cucs_storage_flex_flash_controller_controller_state:ffc_software_err',
            'cucs_storage_flex_flash_controller_dn:their oxen oxen Jaded their Jaded',
            'cucs_storage_flex_flash_controller_flex_flash_type:unknown',
            'cucs_storage_flex_flash_controller_has_error:no_error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:na',
            'cucs_storage_flex_flash_controller_model:Jaded kept',
            'cucs_storage_flex_flash_controller_oper_state:accessibility_problem',
            'cucs_storage_flex_flash_controller_operability:powered_off',
            'cucs_storage_flex_flash_controller_operating_mode:unknown',
            'cucs_storage_flex_flash_controller_perf:lower_non_recoverable',
            'cucs_storage_flex_flash_controller_physical_drive_count:4231826167',
            'cucs_storage_flex_flash_controller_power:power_save',
            'cucs_storage_flex_flash_controller_presence:inaccessible',
            'cucs_storage_flex_flash_controller_type:hba',
            'cucs_storage_flex_flash_controller_vendor:oxen their oxen forward forward oxen forward but',
            'cucs_storage_flex_flash_controller_virtual_drive_count:2476043555',
        ],
        [
            'cucs_storage_flex_flash_controller_controller_health:ffch_flexd_error_sd_op_mode_mismatch_with_un',
            'cucs_storage_flex_flash_controller_controller_state:ffc_software_err',
            'cucs_storage_flex_flash_controller_dn:Jaded but but',
            'cucs_storage_flex_flash_controller_flex_flash_type:fx3s',
            'cucs_storage_flex_flash_controller_has_error:no_error',
            'cucs_storage_flex_flash_controller_is_format_fsm_running:no',
            'cucs_storage_flex_flash_controller_model:but zombies',
            'cucs_storage_flex_flash_controller_oper_state:operable',
            'cucs_storage_flex_flash_controller_operability:voltage_problem',
            'cucs_storage_flex_flash_controller_operating_mode:util',
            'cucs_storage_flex_flash_controller_perf:lower_critical',
            'cucs_storage_flex_flash_controller_physical_drive_count:1941385615',
            'cucs_storage_flex_flash_controller_power:power_save',
            'cucs_storage_flex_flash_controller_presence:mismatch_identity_unestablishable',
            'cucs_storage_flex_flash_controller_type:unknown',
            'cucs_storage_flex_flash_controller_vendor:kept oxen oxen forward',
            'cucs_storage_flex_flash_controller_virtual_drive_count:1041628876',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsStorageFlexFlashController', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'cucs_storage_flex_flash_drive_connection_protocol:nvme',
            'cucs_storage_flex_flash_drive_dn:driving quaintly Jaded forward',
            'cucs_storage_flex_flash_drive_drive_type:unknown',
            'cucs_storage_flex_flash_drive_model:zombies acted acted',
            'cucs_storage_flex_flash_drive_name:forward kept quaintly driving zombies but Jaded forward zombies',
            'cucs_storage_flex_flash_drive_operability:accessibility_problem',
            'cucs_storage_flex_flash_drive_operation_state:partition_non_mirrored_updating_success',
            'cucs_storage_flex_flash_drive_presence:equipped_identity_unestablishable',
            'cucs_storage_flex_flash_drive_removable:na',
            'cucs_storage_flex_flash_drive_rw_type:read_write',
            'cucs_storage_flex_flash_drive_state:raid',
            'cucs_storage_flex_flash_drive_visible:yes',
        ],
        [
            'cucs_storage_flex_flash_drive_connection_protocol:sas',
            'cucs_storage_flex_flash_drive_dn:kept zombies zombies their acted',
            'cucs_storage_flex_flash_drive_drive_type:huu',
            'cucs_storage_flex_flash_drive_model:forward zombies Jaded',
            'cucs_storage_flex_flash_drive_name:quaintly their but but',
            'cucs_storage_flex_flash_drive_operability:thermal_problem',
            'cucs_storage_flex_flash_drive_operation_state:partition_mirrored_updating_fail',
            'cucs_storage_flex_flash_drive_presence:mismatch_identity_unestablishable',
            'cucs_storage_flex_flash_drive_removable:no',
            'cucs_storage_flex_flash_drive_rw_type:read_write',
            'cucs_storage_flex_flash_drive_state:raid',
            'cucs_storage_flex_flash_drive_visible:no',
        ],
        [
            'cucs_storage_flex_flash_drive_connection_protocol:sas',
            'cucs_storage_flex_flash_drive_dn:quaintly kept zombies Jaded their zombies quaintly their',
            'cucs_storage_flex_flash_drive_drive_type:huu',
            'cucs_storage_flex_flash_drive_model:acted zombies quaintly forward kept Jaded quaintly',
            'cucs_storage_flex_flash_drive_name:oxen acted acted driving their acted their kept oxen',
            'cucs_storage_flex_flash_drive_operability:backplane_port_problem',
            'cucs_storage_flex_flash_drive_operation_state:partition_mirrored',
            'cucs_storage_flex_flash_drive_presence:equipped',
            'cucs_storage_flex_flash_drive_removable:na',
            'cucs_storage_flex_flash_drive_rw_type:read_write',
            'cucs_storage_flex_flash_drive_state:raid',
            'cucs_storage_flex_flash_drive_visible:no',
        ],
        [
            'cucs_storage_flex_flash_drive_connection_protocol:sata',
            'cucs_storage_flex_flash_drive_dn:but',
            'cucs_storage_flex_flash_drive_drive_type:huu',
            'cucs_storage_flex_flash_drive_model:quaintly driving quaintly quaintly their',
            'cucs_storage_flex_flash_drive_name:Jaded Jaded Jaded acted forward',
            'cucs_storage_flex_flash_drive_operability:malformed_fru',
            'cucs_storage_flex_flash_drive_operation_state:partition_non_mirrored_erasing_success',
            'cucs_storage_flex_flash_drive_presence:mismatch_slave',
            'cucs_storage_flex_flash_drive_removable:na',
            'cucs_storage_flex_flash_drive_rw_type:read_only',
            'cucs_storage_flex_flash_drive_state:raid',
            'cucs_storage_flex_flash_drive_visible:yes',
        ],
        [
            'cucs_storage_flex_flash_drive_connection_protocol:sata',
            'cucs_storage_flex_flash_drive_dn:forward',
            'cucs_storage_flex_flash_drive_drive_type:unknown',
            'cucs_storage_flex_flash_drive_model:acted acted oxen oxen forward',
            'cucs_storage_flex_flash_drive_name:Jaded',
            'cucs_storage_flex_flash_drive_operability:disabled',
            'cucs_storage_flex_flash_drive_operation_state:partition_mirrored_erasing_success',
            'cucs_storage_flex_flash_drive_presence:empty',
            'cucs_storage_flex_flash_drive_removable:na',
            'cucs_storage_flex_flash_drive_rw_type:read_write',
            'cucs_storage_flex_flash_drive_state:raid',
            'cucs_storage_flex_flash_drive_visible:yes',
        ],
        [
            'cucs_storage_flex_flash_drive_connection_protocol:sata',
            'cucs_storage_flex_flash_drive_dn:kept',
            'cucs_storage_flex_flash_drive_drive_type:huu',
            'cucs_storage_flex_flash_drive_model:kept',
            'cucs_storage_flex_flash_drive_name:kept quaintly',
            'cucs_storage_flex_flash_drive_operability:powered_off',
            'cucs_storage_flex_flash_drive_operation_state:unknown',
            'cucs_storage_flex_flash_drive_presence:mismatch',
            'cucs_storage_flex_flash_drive_removable:yes',
            'cucs_storage_flex_flash_drive_rw_type:read_write',
            'cucs_storage_flex_flash_drive_state:raid',
            'cucs_storage_flex_flash_drive_visible:yes',
        ],
        [
            'cucs_storage_flex_flash_drive_connection_protocol:sata',
            'cucs_storage_flex_flash_drive_dn:kept oxen their kept but but quaintly kept oxen',
            'cucs_storage_flex_flash_drive_drive_type:huu',
            'cucs_storage_flex_flash_drive_model:oxen quaintly',
            'cucs_storage_flex_flash_drive_name:oxen oxen but quaintly kept kept Jaded quaintly',
            'cucs_storage_flex_flash_drive_operability:operable',
            'cucs_storage_flex_flash_drive_operation_state:partition_mirrored_erasing_success',
            'cucs_storage_flex_flash_drive_presence:equipped_not_primary',
            'cucs_storage_flex_flash_drive_removable:no',
            'cucs_storage_flex_flash_drive_rw_type:read_write',
            'cucs_storage_flex_flash_drive_state:nonraid',
            'cucs_storage_flex_flash_drive_visible:yes',
        ],
        [
            'cucs_storage_flex_flash_drive_connection_protocol:sata',
            'cucs_storage_flex_flash_drive_dn:quaintly acted oxen',
            'cucs_storage_flex_flash_drive_drive_type:huu',
            'cucs_storage_flex_flash_drive_model:zombies kept their oxen their Jaded forward their',
            'cucs_storage_flex_flash_drive_name:Jaded but zombies forward zombies but forward quaintly',
            'cucs_storage_flex_flash_drive_operability:powered_off',
            'cucs_storage_flex_flash_drive_operation_state:partition_mirrored_syncing_success',
            'cucs_storage_flex_flash_drive_presence:mismatch',
            'cucs_storage_flex_flash_drive_removable:yes',
            'cucs_storage_flex_flash_drive_rw_type:read_write',
            'cucs_storage_flex_flash_drive_state:raid',
            'cucs_storage_flex_flash_drive_visible:yes',
        ],
        [
            'cucs_storage_flex_flash_drive_connection_protocol:unspecified',
            'cucs_storage_flex_flash_drive_dn:driving Jaded acted',
            'cucs_storage_flex_flash_drive_drive_type:huu',
            'cucs_storage_flex_flash_drive_model:acted zombies acted forward forward kept Jaded',
            'cucs_storage_flex_flash_drive_name:quaintly driving oxen Jaded their oxen Jaded',
            'cucs_storage_flex_flash_drive_operability:accessibility_problem',
            'cucs_storage_flex_flash_drive_operation_state:partition_mirrored',
            'cucs_storage_flex_flash_drive_presence:missing',
            'cucs_storage_flex_flash_drive_removable:na',
            'cucs_storage_flex_flash_drive_rw_type:read_write',
            'cucs_storage_flex_flash_drive_state:raid',
            'cucs_storage_flex_flash_drive_visible:no',
        ],
        [
            'cucs_storage_flex_flash_drive_connection_protocol:unspecified',
            'cucs_storage_flex_flash_drive_dn:zombies driving driving kept acted',
            'cucs_storage_flex_flash_drive_drive_type:hv',
            'cucs_storage_flex_flash_drive_model:their forward Jaded zombies quaintly Jaded',
            'cucs_storage_flex_flash_drive_name:oxen but acted their',
            'cucs_storage_flex_flash_drive_operability:backplane_port_problem',
            'cucs_storage_flex_flash_drive_operation_state:partition_mirrored_syncing',
            'cucs_storage_flex_flash_drive_presence:equipped_identity_unestablishable',
            'cucs_storage_flex_flash_drive_removable:yes',
            'cucs_storage_flex_flash_drive_rw_type:read_only',
            'cucs_storage_flex_flash_drive_state:nonraid',
            'cucs_storage_flex_flash_drive_visible:no',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cucsStorageFlexFlashDriveSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'cisco-ucs Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cisco-ucs.device.name',
        'profile': 'cisco-ucs',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.12.3.1.3.1062',
        'vendor': 'cisco',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
