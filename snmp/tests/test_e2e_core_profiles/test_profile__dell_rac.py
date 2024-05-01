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
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile__dell_rac(dd_agent_check):
    profile = '_dell-rac'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dell-rac',
        'snmp_host:_dell-rac.device.name',
        'device_hostname:_dell-rac.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.drsCMCCurrStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.drsGlobalCurrStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.drsGlobalSystemStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.drsPowerCurrStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.drsRedCurrStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['chassis_index:24'],
        ['chassis_index:27'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.systemStateAmperageStatusCombined', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStateChassisIntrusionStatusCombined', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStateChassisStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStateCoolingDeviceStatusCombined', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStateCoolingUnitStatusCombined', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStateCoolingUnitStatusRedundancy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStateMemoryDeviceStatusCombined', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStatePowerSupplyStatusCombined', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStatePowerUnitStatusCombined', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStatePowerUnitStatusRedundancy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStateProcessorDeviceStatusCombined', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.systemStateTemperatureStatisticsStatusCombined',
            metric_type=aggregator.GAUGE,
            tags=common_tags + tag_row,
        )
        aggregator.assert_metric(
            'snmp.systemStateTemperatureStatusCombined', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'chassis_index:24',
            'system_state_chassis_status:critical',
            'system_state_power_unit_status_redundancy:not_redundant',
            'system_state_power_supply_status_combined:non_recoverable',
            'system_state_amperage_status_combined:unknown',
            'system_state_cooling_unit_status_redundancy:full',
            'system_state_cooling_device_status_combined:non_recoverable',
            'system_state_temperature_status_combined:unknown',
            'system_state_memory_device_status_combined:critical',
            'system_state_chassis_intrusion_status_combined:other',
            'system_state_power_unit_status_combined:critical',
            'system_state_cooling_unit_status_combined:critical',
            'system_state_processor_device_status_combined:unknown',
            'system_state_temperature_statistics_status_combined:critical',
        ],
        [
            'chassis_index:27',
            'system_state_chassis_status:ok',
            'system_state_power_unit_status_redundancy:not_redundant',
            'system_state_power_supply_status_combined:other',
            'system_state_amperage_status_combined:ok',
            'system_state_cooling_unit_status_redundancy:redundancy_offline',
            'system_state_cooling_device_status_combined:unknown',
            'system_state_temperature_status_combined:other',
            'system_state_memory_device_status_combined:non_critical',
            'system_state_chassis_intrusion_status_combined:other',
            'system_state_power_unit_status_combined:unknown',
            'system_state_cooling_unit_status_combined:non_critical',
            'system_state_processor_device_status_combined:critical',
            'system_state_temperature_statistics_status_combined:unknown',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.systemState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['disk_name:acted oxen quaintly zombies zombies driving their forward'],
        ['disk_name:zombies zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.physicalDiskCapacityInMB', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.physicalDiskFreeSpaceInMB', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.physicalDiskState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.physicalDiskUsedSpaceInMB', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['disk_number:3', 'disk_state:nonraid', 'disk_name:zombies zombies'],
        ['disk_number:14', 'disk_state:ready', 'disk_name:acted oxen quaintly zombies zombies driving their forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.physicalDisk', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'enclosure_power_supply_fqdd:acted but oxen oxen but their quaintly acted Jaded',
            'enclosure_power_supply_number:22',
            'supply_name:kept their quaintly forward oxen',
        ],
        [
            'enclosure_power_supply_fqdd:but zombies driving',
            'enclosure_power_supply_number:24',
            'supply_name:quaintly driving',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'enclosure_power_supply_fqdd:acted but oxen oxen but their quaintly acted Jaded',
            'enclosure_power_supply_number:22',
            'enclosure_power_supply_state:failed',
            'supply_name:kept their quaintly forward oxen',
        ],
        [
            'enclosure_power_supply_fqdd:but zombies driving',
            'enclosure_power_supply_number:24',
            'enclosure_power_supply_state:degraded',
            'supply_name:quaintly driving',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.enclosurePowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['battery_fqdd:kept Jaded driving', 'battery_name:acted'],
        ['battery_fqdd:kept zombies', 'battery_name:driving their forward acted'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.batteryState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['battery_fqdd:kept Jaded driving', 'battery_name:acted', 'battery_state:failed'],
        ['battery_fqdd:kept zombies', 'battery_name:driving their forward acted', 'battery_state:charging'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.battery', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'controller_fqdd:driving acted driving kept driving but their oxen but',
            'controller_name:oxen',
            'controller_number:10',
            'controller_pci_slot:forward oxen but kept',
        ],
        [
            'controller_fqdd:quaintly zombies Jaded acted kept',
            'controller_name:acted oxen',
            'controller_number:26',
            'controller_pci_slot:kept driving zombies acted driving',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.controllerRollUpStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'controller_fqdd:driving acted driving kept driving but their oxen but',
            'controller_name:oxen',
            'controller_number:10',
            'controller_pci_slot:forward oxen but kept',
            'controller_roll_up_status:unknown',
        ],
        [
            'controller_fqdd:quaintly zombies Jaded acted kept',
            'controller_name:acted oxen',
            'controller_number:26',
            'controller_pci_slot:kept driving zombies acted driving',
            'controller_roll_up_status:non_recoverable',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.controller', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:25', 'device_descr_name:driving their oxen forward'],
        ['chassis_index:30', 'device_descr_name:driving'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.pCIDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:25', 'device_descr_name:driving their oxen forward', 'device_status:non_critical'],
        ['chassis_index:30', 'device_descr_name:driving', 'device_status:non_recoverable'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.pCIDevice', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:25', 'slot_name:zombies driving forward but Jaded acted kept acted'],
        ['chassis_index:27', 'slot_name:Jaded oxen their acted Jaded kept quaintly'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.systemSlotStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:25',
            'slot_name:zombies driving forward but Jaded acted kept acted',
            'slot_status:non_recoverable',
        ],
        ['chassis_index:27', 'slot_name:Jaded oxen their acted Jaded kept quaintly', 'slot_status:non_recoverable'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.systemSlot', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:13', 'device_fqdd:quaintly', 'mac_addr:aaaaaa'],
        ['chassis_index:24', 'device_fqdd:oxen acted zombies but Jaded', 'mac_addr:aaaaaa'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.networkDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:13',
            'device_index:15',
            'device_fqdd:quaintly',
            'mac_addr:aaaaaa',
            'network_device_status:non_recoverable',
        ],
        [
            'chassis_index:24',
            'device_index:7',
            'device_fqdd:oxen acted zombies but Jaded',
            'mac_addr:aaaaaa',
            'network_device_status:non_recoverable',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.networkDevice', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:28', 'system_bios_index:12'],
        ['chassis_index:29', 'system_bios_index:19'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.systemBIOSStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:28', 'system_bios_index:12', 'system_bios_status:other'],
        ['chassis_index:29', 'system_bios_index:19', 'system_bios_status:non_recoverable'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.systemBIOS', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:11', 'intrusion_index:5', 'intrusion_location_name:driving zombies Jaded zombies'],
        ['chassis_index:15', 'intrusion_index:12', 'intrusion_location_name:their driving quaintly'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.intrusionReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.intrusionStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:14',
            'power_supply_fqdd:quaintly forward but but zombies their driving acted',
            'power_supply_index:17',
        ],
        [
            'chassis_index:15',
            'power_supply_fqdd:driving zombies but driving quaintly Jaded zombies forward',
            'power_supply_index:8',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.powerSupplyCurrentInputVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.powerSupplyMaximumInputVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.powerSupplyOutputWatts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['amperage_probe_index:12', 'chassis_index:13', 'probe_type:amperage_probe_type_is_minus12_volt'],
        ['amperage_probe_index:16', 'chassis_index:3', 'probe_type:amperage_probe_type_is_1point5_volt'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.amperageProbeReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.amperageProbeStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'amperage_probe_index:12',
            'chassis_index:13',
            'probe_type:amperage_probe_type_is_minus12_volt',
            'amperage_probe_status:other',
        ],
        [
            'amperage_probe_index:16',
            'chassis_index:3',
            'probe_type:amperage_probe_type_is_1point5_volt',
            'amperage_probe_status:critical_lower',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.amperageProbe', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:26', 'power_usage_entity_name:zombies their', 'power_usage_index:8'],
        ['chassis_index:6', 'power_usage_entity_name:forward kept', 'power_usage_index:11'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.powerUsageStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:14', 'probe_type:voltage_probe_type_is_memory_status', 'voltage_probe_index:21'],
        ['chassis_index:29', 'probe_type:voltage_probe_type_is_1point5_volt', 'voltage_probe_index:25'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.voltageProbeReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.voltageProbeStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:14',
            'probe_type:voltage_probe_type_is_memory_status',
            'voltage_probe_index:21',
            'voltage_probe_status:failed',
        ],
        [
            'chassis_index:29',
            'probe_type:voltage_probe_type_is_1point5_volt',
            'voltage_probe_index:25',
            'voltage_probe_status:critical_lower',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.voltageProbe', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:24', 'system_battery_index:29', 'system_battery_location_name:forward oxen Jaded zombies but'],
        ['chassis_index:3', 'system_battery_index:15', 'system_battery_location_name:zombies their but quaintly their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.systemBatteryReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.systemBatteryStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:11', 'cooling_unit_index:4', 'cooling_unit_name:zombies'],
        ['chassis_index:12', 'cooling_unit_index:10', 'cooling_unit_name:quaintly'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.coolingUnitRedundancyStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.coolingUnitStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:2',
            'cooling_device_fqdd:driving oxen oxen oxen their',
            'cooling_device_location_name:quaintly driving forward kept zombies quaintly acted oxen',
            'cooling_device_name:13',
            'cooling_device_type:cooling_device_type_is_a_blower',
        ],
        [
            'chassis_index:28',
            'cooling_device_fqdd:kept forward oxen their quaintly oxen oxen zombies driving',
            'cooling_device_location_name:forward quaintly zombies acted quaintly',
            'cooling_device_name:28',
            'cooling_device_type:cooling_device_type_is_active_cooling',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.coolingDeviceDiscreteReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.coolingDeviceReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.coolingDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:10',
            'temperature_probe_index:14',
            'temperature_probe_location_name:but',
            'temperature_probe_type:temperature_probe_type_is_ambient_esm',
        ],
        [
            'chassis_index:3',
            'temperature_probe_index:18',
            'temperature_probe_location_name:quaintly forward driving zombies oxen their oxen',
            'temperature_probe_type:temperature_probe_type_is_unknown',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.temperatureProbeDiscreteReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.temperatureProbeReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.temperatureProbeStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'chassis_index:2',
            'processor_device_brand_name:driving oxen',
            'processor_device_fqdd:zombies their but acted Jaded quaintly quaintly acted forward',
            'processor_device_index:11',
        ],
        [
            'chassis_index:30',
            'processor_device_brand_name:zombies oxen kept Jaded Jaded',
            'processor_device_fqdd:oxen their oxen',
            'processor_device_index:30',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.processorDeviceCurrentSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.processorDeviceMaximumSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.processorDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.processorDeviceVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['chassis_index:5', 'processor_device_status_index:30', 'processor_device_status_location_name:Jaded forward'],
        [
            'chassis_index:7',
            'processor_device_status_index:13',
            'processor_device_status_location_name:acted Jaded their quaintly zombies driving but forward Jaded',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.processorDeviceStatusReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.processorDeviceStatusStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['chassis_index:15', 'device_index:23', 'device_type:11'],
        ['chassis_index:22', 'device_index:23', 'device_type:24'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memoryDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:15', 'device_index:23', 'device_type:device_type_is_feprom', 'memory_device_status:unknown'],
        ['chassis_index:22', 'device_index:23', 'device_type:device_type_is_ddr3', 'memory_device_status:other'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.memoryDevice', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:29', 'fru_fqdd:forward acted kept oxen', 'fru_index:20'],
        ['chassis_index:30', 'fru_fqdd:driving kept', 'fru_index:7'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fruInformationStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'virtual_disk_fqdd:oxen oxen Jaded forward kept forward',
            'virtual_disk_name:Jaded driving zombies driving driving forward oxen quaintly driving',
            'virtual_disk_number:15',
        ],
        [
            'virtual_disk_fqdd:zombies kept their',
            'virtual_disk_name:kept Jaded their quaintly their acted',
            'virtual_disk_number:22',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.virtualDiskComponentStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.virtualDiskSizeInMB', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.virtualDiskState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.virtualDiskT10PIStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['chassis_index:1', 'drs_psu_index:3'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.drsAmpsReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.drsWattsReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:1', 'drs_psu_index:3'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.drsKWhCumulative', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': '_dell-rac Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_dell-rac.device.name',
        'profile': 'dell-rac',
        'status': 1,
        'sys_object_id': '1.2.3.1003',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
