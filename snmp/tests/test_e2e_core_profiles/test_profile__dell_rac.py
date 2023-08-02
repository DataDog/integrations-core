# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile__dell_rac(dd_agent_check):
    config = create_e2e_core_test_config('_dell-rac')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dell-rac',
        'snmp_host:_dell-rac.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
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
        ['chassis_index:10', 'system_state_power_supply_status_combined:unknown'],
        ['chassis_index:27', 'system_state_power_supply_status_combined:unknown'],
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
            'snmp.systemStatePowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
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
        ['disk_name:but quaintly Jaded acted but quaintly'],
        ['disk_name:kept oxen driving their their'],
        ['disk_name:oxen driving their acted forward driving'],
        ['disk_name:quaintly'],
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
        [
            'enclosure_power_supply_fqdd:but driving oxen quaintly kept their',
            'enclosure_power_supply_number:7',
            'enclosure_power_supply_state:ready',
            'supply_name:oxen oxen driving oxen',
        ],
        [
            'enclosure_power_supply_fqdd:kept',
            'enclosure_power_supply_number:3',
            'enclosure_power_supply_state:ready',
            'supply_name:oxen but kept oxen acted',
        ],
        [
            'enclosure_power_supply_fqdd:their Jaded acted forward but oxen acted',
            'enclosure_power_supply_number:15',
            'enclosure_power_supply_state:unknown',
            'supply_name:forward their Jaded quaintly oxen acted',
        ],
        [
            'enclosure_power_supply_fqdd:their driving their Jaded their acted kept Jaded',
            'enclosure_power_supply_number:16',
            'enclosure_power_supply_state:ready',
            'supply_name:their but',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.enclosurePowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['battery_fqdd:but Jaded kept driving', 'battery_name:zombies their'],
        ['battery_fqdd:forward but', 'battery_name:kept driving but oxen Jaded zombies driving driving forward'],
        ['battery_fqdd:kept zombies Jaded zombies', 'battery_name:oxen'],
        ['battery_fqdd:their zombies', 'battery_name:but oxen quaintly but quaintly zombies kept forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.batteryState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'controller_fqdd:forward Jaded their',
            'controller_name:but Jaded acted driving oxen zombies quaintly',
            'controller_number:4',
            'controller_pci_slot:acted oxen driving acted but quaintly kept but',
        ],
        [
            'controller_fqdd:kept but zombies oxen forward their',
            'controller_name:oxen Jaded kept their zombies',
            'controller_number:20',
            'controller_pci_slot:quaintly kept quaintly their Jaded',
        ],
        [
            'controller_fqdd:kept oxen quaintly acted',
            'controller_name:Jaded zombies zombies',
            'controller_number:26',
            'controller_pci_slot:zombies their kept zombies acted',
        ],
        [
            'controller_fqdd:zombies acted quaintly',
            'controller_name:zombies quaintly',
            'controller_number:15',
            'controller_pci_slot:zombies but forward zombies',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.controllerRollUpStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['chassis_index:1', 'device_descr_name:oxen'],
        ['chassis_index:11', 'device_descr_name:forward their oxen kept their their zombies their zombies'],
        ['chassis_index:23', 'device_descr_name:kept but'],
        ['chassis_index:30', 'device_descr_name:kept driving forward quaintly kept kept zombies but'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.pCIDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:16', 'slot_name:their'],
        ['chassis_index:24', 'slot_name:acted forward forward'],
        ['chassis_index:26', 'slot_name:quaintly Jaded zombies'],
        ['chassis_index:6', 'slot_name:kept driving oxen oxen oxen zombies their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.systemSlotStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:2', 'device_fqdd:their'],
        ['chassis_index:20', 'device_fqdd:zombies'],
        ['chassis_index:29', 'device_fqdd:acted acted kept'],
        ['chassis_index:9', 'device_fqdd:oxen oxen Jaded zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.networkDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:18', 'system_bios_index:7'],
        ['chassis_index:31', 'system_bios_index:16'],
        ['chassis_index:8', 'system_bios_index:17'],
        ['chassis_index:8', 'system_bios_index:29'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.systemBIOSStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:25',
            'intrusion_index:4',
            'intrusion_location_name:forward oxen but driving oxen Jaded zombies forward acted',
        ],
        [
            'chassis_index:29',
            'intrusion_index:28',
            'intrusion_location_name:oxen but driving Jaded Jaded Jaded driving',
        ],
        ['chassis_index:4', 'intrusion_index:6', 'intrusion_location_name:oxen oxen'],
        ['chassis_index:6', 'intrusion_index:26', 'intrusion_location_name:oxen forward driving'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.intrusionReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.intrusionStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:17', 'device_fqdd:acted their', 'power_supply_index:4'],
        ['chassis_index:23', 'device_fqdd:oxen', 'power_supply_index:27'],
        ['chassis_index:26', 'device_fqdd:zombies but forward Jaded zombies their zombies but', 'power_supply_index:4'],
        ['chassis_index:9', 'device_fqdd:zombies Jaded quaintly', 'power_supply_index:4'],
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
        ['amperage_probe_index:24', 'chassis_index:23', 'probe_type:26'],
        ['amperage_probe_index:28', 'chassis_index:27', 'probe_type:4'],
        ['amperage_probe_index:4', 'chassis_index:11', 'probe_type:13'],
        ['amperage_probe_index:9', 'chassis_index:4', 'probe_type:7'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.amperageProbeReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.amperageProbeStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:11', 'power_usage_entity_name:forward zombies Jaded', 'power_usage_index:24'],
        ['chassis_index:13', 'power_usage_entity_name:oxen Jaded kept', 'power_usage_index:24'],
        ['chassis_index:3', 'power_usage_entity_name:acted', 'power_usage_index:30'],
        ['chassis_index:5', 'power_usage_entity_name:forward forward acted their', 'power_usage_index:1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.powerUsageStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:11', 'probe_type:9', 'voltage_probe_index:28'],
        ['chassis_index:19', 'probe_type:13', 'voltage_probe_index:22'],
        ['chassis_index:21', 'probe_type:7', 'voltage_probe_index:2'],
        ['chassis_index:5', 'probe_type:19', 'voltage_probe_index:29'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.voltageProbeReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.voltageProbeStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:11', 'system_battery_index:26', 'system_battery_location_name:kept acted oxen quaintly'],
        [
            'chassis_index:21',
            'system_battery_index:27',
            'system_battery_location_name:zombies forward acted quaintly acted acted quaintly driving oxen',
        ],
        ['chassis_index:27', 'system_battery_index:9', 'system_battery_location_name:zombies'],
        ['chassis_index:7', 'system_battery_index:27', 'system_battery_location_name:quaintly'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.systemBatteryReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.systemBatteryStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:16', 'cooling_unit_index:10', 'cooling_unit_name:kept their kept'],
        [
            'chassis_index:17',
            'cooling_unit_index:11',
            'cooling_unit_name:Jaded kept driving their their their kept acted',
        ],
        ['chassis_index:18', 'cooling_unit_index:25', 'cooling_unit_name:but but their zombies zombies zombies acted'],
        ['chassis_index:8', 'cooling_unit_index:12', 'cooling_unit_name:their kept forward forward zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.coolingUnitRedundancyStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.coolingUnitStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:17',
            'cooling_device_fqdd:Jaded forward but forward acted',
            'cooling_device_location_name:Jaded their kept quaintly oxen but acted quaintly',
            'cooling_device_name:11',
            'cooling_device_type:11',
        ],
        [
            'chassis_index:22',
            'cooling_device_fqdd:driving oxen acted',
            'cooling_device_location_name:but but forward quaintly forward Jaded acted',
            'cooling_device_name:24',
            'cooling_device_type:6',
        ],
        [
            'chassis_index:30',
            'cooling_device_fqdd:quaintly Jaded zombies quaintly quaintly driving their acted Jaded',
            'cooling_device_location_name:Jaded',
            'cooling_device_name:15',
            'cooling_device_type:9',
        ],
        [
            'chassis_index:31',
            'cooling_device_fqdd:forward their quaintly acted zombies their quaintly',
            'cooling_device_location_name:zombies kept',
            'cooling_device_name:26',
            'cooling_device_type:9',
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
            'chassis_index:20',
            'temperature_probe_index:25',
            'temperature_probe_location_name:driving quaintly their acted oxen forward',
            'temperature_probe_type:2',
        ],
        [
            'chassis_index:20',
            'temperature_probe_index:4',
            'temperature_probe_location_name:driving zombies oxen zombies forward Jaded but forward',
            'temperature_probe_type:16',
        ],
        [
            'chassis_index:22',
            'temperature_probe_index:3',
            'temperature_probe_location_name:Jaded',
            'temperature_probe_type:2',
        ],
        [
            'chassis_index:4',
            'temperature_probe_index:10',
            'temperature_probe_location_name:Jaded but driving kept but acted forward zombies',
            'temperature_probe_type:3',
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
            'chassis_index:18',
            'processor_device_brand_name:but kept',
            'processor_device_fqdd:oxen forward but Jaded but driving driving zombies',
            'processor_device_index:20',
        ],
        [
            'chassis_index:18',
            'processor_device_brand_name:zombies',
            'processor_device_fqdd:oxen driving oxen zombies but quaintly quaintly driving',
            'processor_device_index:9',
        ],
        [
            'chassis_index:26',
            'processor_device_brand_name:their driving quaintly oxen quaintly driving zombies',
            'processor_device_fqdd:oxen quaintly',
            'processor_device_index:3',
        ],
        [
            'chassis_index:8',
            'processor_device_brand_name:but Jaded acted but',
            'processor_device_fqdd:driving oxen acted Jaded Jaded zombies zombies zombies',
            'processor_device_index:26',
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
        [
            'chassis_index:11',
            'processor_device_status_index:20',
            'processor_device_status_location_name:zombies their acted acted quaintly',
        ],
        [
            'chassis_index:16',
            'processor_device_status_index:8',
            'processor_device_status_location_name:driving forward Jaded forward',
        ],
        [
            'chassis_index:20',
            'processor_device_status_index:23',
            'processor_device_status_location_name:but but forward driving oxen',
        ],
        [
            'chassis_index:8',
            'processor_device_status_index:14',
            'processor_device_status_location_name:driving Jaded driving driving',
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
        ['chassis_index:12', 'device_index:22', 'device_type:7'],
        ['chassis_index:17', 'device_index:4', 'device_type:17'],
        ['chassis_index:24', 'device_index:1', 'device_type:9'],
        ['chassis_index:24', 'device_index:13', 'device_type:26'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memoryDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:13', 'fru_fqdd:driving kept acted', 'fru_index:7'],
        ['chassis_index:17', 'fru_fqdd:oxen forward kept kept', 'fru_index:3'],
        ['chassis_index:17', 'fru_fqdd:quaintly forward acted oxen their but quaintly but their', 'fru_index:30'],
        ['chassis_index:19', 'fru_fqdd:zombies forward but their acted but', 'fru_index:19'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fruInformationStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'virtual_disk_fqdd:Jaded but zombies their oxen',
            'virtual_disk_name:their oxen but forward forward driving zombies zombies',
            'virtual_disk_number:31',
        ],
        [
            'virtual_disk_fqdd:Jaded oxen oxen their quaintly forward',
            'virtual_disk_name:oxen',
            'virtual_disk_number:28',
        ],
        [
            'virtual_disk_fqdd:quaintly quaintly their acted their acted zombies Jaded Jaded',
            'virtual_disk_name:kept quaintly oxen but kept forward driving',
            'virtual_disk_number:4',
        ],
        ['virtual_disk_fqdd:zombies but their', 'virtual_disk_name:their quaintly', 'virtual_disk_number:26'],
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
        ['chassis_index:1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.drsAmpsReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.drsWattsReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:1'],
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
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
