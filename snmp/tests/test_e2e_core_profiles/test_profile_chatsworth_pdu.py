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


def test_e2e_profile_chatsworth_pdu(dd_agent_check):
    profile = 'chatsworth_pdu'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:chatsworth_pdu',
        'snmp_host:chatsworth_pdu.device.name',
        'device_hostname:chatsworth_pdu.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
        'device_vendor:chatsworth',
    ] + [
        'legacy_pdu_macaddress:00:0E:D3:AA:CC:EE',
        'legacy_pdu_model:P10-1234-ABC',
        'legacy_pdu_name:legacy-name1',
        'legacy_pdu_version:1.3.6.1.4.1.30932.1.1',
    ]

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.currentxy1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.currentxy2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.currentyz1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.currentyz2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.currentzx1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.currentzx2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.energyxy1s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.energyxy2s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.energyyz1s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.energyyz2s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.energyzx1s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.energyzx2s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.humidityProbe1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.humidityProbe2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.line1curr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.line2curr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.line3curr', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outOfService', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet10Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet11Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet12Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet13Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet14Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet15Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet16Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet17Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet18Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet19Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet1Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet20Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet21Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet22Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet23Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet24Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet2Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet3Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet4Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet5Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet6Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet7Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet8Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.outlet9Current', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.pduRole', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerFactxy1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerFactxy2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerFactyz1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerFactyz2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerFactzx1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerFactzx2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerxy1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerxy2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.poweryz1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.poweryz2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerzx1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.powerzx2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet10s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet11s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet12s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet13s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet14s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet15s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet16s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet17s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet18s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet19s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet1s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet20s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet21s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet22s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet23s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet24s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet2s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet3s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet4s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet5s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet6s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet7s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet8s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.receptacleEnergyoutlet9s', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.temperatureProbe1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.temperatureProbe2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.voltagexy1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.voltagexy2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.voltageyz1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.voltageyz2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.voltagezx1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.voltagezx2', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'pdu_cabinetid:cab1',
            'pdu_ipaddress:42.2.210.224',
            'pdu_macaddress:0x111111111111',
            'pdu_model:model1',
            'pdu_name:name1',
            'pdu_version:v1.1',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpiPduChainRole', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduNumberBranches', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduNumberOutlets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduOutOfService', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduTotalPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduUpgrade', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['lock_id:1'],
        ['lock_id:2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpiPduDoorStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduEasStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduLockStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['eas_status:inactive', 'lock_id:front', 'lock_status:closed', 'door_status:open'],
        ['eas_status:ready', 'lock_id:rear', 'lock_status:closed', 'door_status:closed'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpiEas', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['sensor_index:20', 'sensor_name:sensor2', 'sensor_type:1'],
        ['sensor_index:26'],
        ['sensor_index:31'],
        ['sensor_index:8', 'sensor_name:sensor1', 'sensor_type:1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpiPduSensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['line_id:14'],
        ['line_id:7'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpiPduLineCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['branch_id:11', 'pdu_name:name1'],
        ['branch_id:7', 'pdu_name:name1'],
        ['pdu_name:name1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpiPduBranchCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cpiPduBranchMaxCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.cpiPduBranchPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cpiPduBranchPowerFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.cpiPduBranchStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduBranchVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['branch_id:11', 'pdu_name:name1'],
        ['branch_id:7', 'pdu_name:name1'],
        ['pdu_name:name1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpiPduBranchEnergy', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    tag_rows = [
        ['outlet_branchid:17', 'outlet_id:5', 'outlet_name:outlet1'],
        ['outlet_branchid:4', 'outlet_id:22', 'outlet_name:outlet2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpiPduOutletCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduOutletPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduOutletStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpiPduOutletVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['outlet_branchid:17', 'outlet_id:5', 'outlet_name:outlet1'],
        ['outlet_branchid:4', 'outlet_id:22', 'outlet_name:outlet2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpiPduOutletEnergy', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'chatsworth_pdu Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'chatsworth_pdu.device.name',
        'profile': 'chatsworth_pdu',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.30932.1.1',
        'vendor': 'chatsworth',
        'device_type': 'pdu',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
