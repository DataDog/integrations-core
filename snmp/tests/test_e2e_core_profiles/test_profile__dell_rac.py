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
        ['chassis_index:10', 'system_state_power_supply_status_combined:noncritical'],
        ['chassis_index:13', 'system_state_power_supply_status_combined:unknown'],
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
        aggregator.assert_metric('snmp.systemState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
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
        ['disk_name:but zombies their quaintly forward zombies kept quaintly Jaded'],
        ['disk_name:oxen Jaded but zombies driving kept driving'],
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
            'enclosure_power_supply_fqdd:forward Jaded oxen kept Jaded oxen zombies their their',
            'enclosure_power_supply_number:23',
            'enclosure_power_supply_state:failed',
            'supply_name:forward quaintly acted Jaded quaintly',
        ],
        [
            'enclosure_power_supply_fqdd:quaintly driving kept quaintly quaintly their kept kept',
            'enclosure_power_supply_number:25',
            'enclosure_power_supply_state:unknown',
            'supply_name:quaintly but',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.enclosurePowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['battery_fqdd:kept acted forward zombies driving zombies', 'battery_name:but zombies quaintly their but'],
        ['battery_fqdd:zombies zombies kept acted forward oxen oxen', 'battery_name:their zombies forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.batteryState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'controller_fqdd:forward their acted but forward kept driving acted',
            'controller_name:zombies quaintly their',
            'controller_number:29',
            'controller_pci_slot:zombies oxen quaintly acted forward their Jaded acted',
        ],
        [
            'controller_fqdd:oxen oxen driving but acted but but zombies oxen',
            'controller_name:zombies but acted',
            'controller_number:5',
            'controller_pci_slot:acted',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.controllerRollUpStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['chassis_index:31', 'device_descr_name:oxen forward oxen their but'],
        ['chassis_index:7', 'device_descr_name:kept acted zombies forward driving oxen their oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.pCIDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:20', 'slot_name:quaintly zombies zombies oxen quaintly their but'],
        ['chassis_index:21', 'slot_name:kept acted quaintly quaintly acted'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.systemSlotStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:18', 'device_fqdd:kept Jaded acted forward their their', 'mac_addr:cdbdew'],
        ['chassis_index:26', 'device_fqdd:quaintly acted forward', 'mac_addr:abcdge'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.networkDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:27', 'system_bios_index:15'],
        ['chassis_index:5', 'system_bios_index:3'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.systemBIOSStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:3', 'intrusion_index:26', 'intrusion_location_name:oxen Jaded'],
        ['chassis_index:7', 'intrusion_index:9', 'intrusion_location_name:quaintly'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.intrusionReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.intrusionStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:18', 'power_supply_fqdd:their quaintly forward', 'power_supply_index:11'],
        [
            'chassis_index:23',
            'power_supply_fqdd:driving oxen acted their forward Jaded kept driving oxen',
            'power_supply_index:22',
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
        ['amperage_probe_index:13', 'chassis_index:10', 'probe_type:12'],
        ['amperage_probe_index:13', 'chassis_index:12', 'probe_type:2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.amperageProbeReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.amperageProbeStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:23', 'power_usage_entity_name:but', 'power_usage_index:12'],
        ['chassis_index:24', 'power_usage_entity_name:but acted their but forward', 'power_usage_index:20'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.powerUsageStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:15', 'probe_type:3', 'voltage_probe_index:31'],
        ['chassis_index:4', 'probe_type:2', 'voltage_probe_index:19'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.voltageProbeReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.voltageProbeStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:1',
            'system_battery_index:27',
            'system_battery_location_name:forward forward forward forward driving their Jaded acted',
        ],
        ['chassis_index:25', 'system_battery_index:1', 'system_battery_location_name:forward their quaintly Jaded'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.systemBatteryReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.systemBatteryStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:16',
            'cooling_unit_index:9',
            'cooling_unit_name:quaintly driving zombies acted their zombies oxen quaintly',
        ],
        ['chassis_index:7', 'cooling_unit_index:21', 'cooling_unit_name:forward zombies driving quaintly'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.coolingUnitRedundancyStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.coolingUnitStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'chassis_index:19',
            'cooling_device_fqdd:zombies their but their but forward',
            'cooling_device_location_name:zombies but zombies forward driving quaintly',
            'cooling_device_name:1',
            'cooling_device_type:10',
        ],
        [
            'chassis_index:21',
            'cooling_device_fqdd:but zombies acted their forward acted',
            'cooling_device_location_name:their',
            'cooling_device_name:10',
            'cooling_device_type:1',
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
            'chassis_index:13',
            'temperature_probe_index:26',
            'temperature_probe_location_name:quaintly',
            'temperature_probe_type:2',
        ],
        [
            'chassis_index:14',
            'temperature_probe_index:8',
            'temperature_probe_location_name:but kept Jaded Jaded their driving zombies zombies',
            'temperature_probe_type:16',
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
            'chassis_index:13',
            'processor_device_brand_name:acted kept quaintly acted kept their zombies Jaded their',
            'processor_device_fqdd:zombies',
            'processor_device_index:20',
        ],
        [
            'chassis_index:13',
            'processor_device_brand_name:kept acted driving',
            'processor_device_fqdd:kept zombies oxen zombies zombies',
            'processor_device_index:11',
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
            'chassis_index:14',
            'processor_device_status_index:16',
            'processor_device_status_location_name:but but but forward quaintly driving',
        ],
        ['chassis_index:4', 'processor_device_status_index:25', 'processor_device_status_location_name:zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.processorDeviceStatusReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.processorDeviceStatusStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['chassis_index:18', 'device_index:11', 'device_type:18'],
        ['chassis_index:21', 'device_index:30', 'device_type:12'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memoryDeviceStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['chassis_index:21', 'fru_fqdd:driving but but driving but oxen driving', 'fru_index:19'],
        ['chassis_index:23', 'fru_fqdd:driving oxen zombies driving driving quaintly acted oxen acted', 'fru_index:12'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fruInformationStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'virtual_disk_fqdd:driving but kept but their quaintly their',
            'virtual_disk_name:kept Jaded zombies quaintly their but kept kept',
            'virtual_disk_number:1',
        ],
        [
            'virtual_disk_fqdd:zombies quaintly kept but',
            'virtual_disk_name:Jaded Jaded quaintly forward oxen',
            'virtual_disk_number:4',
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
