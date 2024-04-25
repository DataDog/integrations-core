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


def test_e2e_profile_huawei(dd_agent_check):
    profile = 'huawei'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:huawei',
        'snmp_host:huawei.device.name',
        'device_hostname:huawei.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + ['huawei_hw_entity_system_model:Jaded but Jaded']

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'huawei_hw_entity_admin_status:not_supported',
            'huawei_hw_entity_board_name:oxen but',
            'huawei_hw_entity_fault_light:not_supported',
            'huawei_hw_entity_oper_status:absent',
            'huawei_hw_entity_standby_status:hot_standby',
        ],
        [
            'huawei_hw_entity_admin_status:not_supported',
            'huawei_hw_entity_board_name:their quaintly',
            'huawei_hw_entity_fault_light:normal',
            'huawei_hw_entity_oper_status:enabled',
            'huawei_hw_entity_standby_status:not_supported',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwEntityTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwEntityVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'huawei_hw_entity_fan_present:absent',
            'huawei_hw_entity_fan_reg:yes',
            'huawei_hw_entity_fan_slot:27',
            'huawei_hw_entity_fan_sn:16',
            'huawei_hw_entity_fan_spd_adj_mode:manual',
            'huawei_hw_entity_fan_state:abnormal',
        ],
        [
            'huawei_hw_entity_fan_present:present',
            'huawei_hw_entity_fan_reg:yes',
            'huawei_hw_entity_fan_slot:18',
            'huawei_hw_entity_fan_sn:10',
            'huawei_hw_entity_fan_spd_adj_mode:manual',
            'huawei_hw_entity_fan_state:abnormal',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwEntityFanSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['huawei_hw_system_power_device_id:26'],
        ['huawei_hw_system_power_device_id:5'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwSystemPowerRemainPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwSystemPowerTotalPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwSystemPowerUsedPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'huawei_hw_ospfv2_nbr_gr_status:normal',
            'huawei_hw_ospfv2_nbr_if_backup_designated_router:206.190.209.237',
            'huawei_hw_ospfv2_nbr_if_designated_router:146.76.41.45',
            'huawei_hw_ospfv2_nbr_mode:slave',
            'huawei_hw_ospfv2_nbr_state:attempt',
            'huawei_hw_ospfv2_neighbor_router_id:10.237.85.65',
            'huawei_hw_ospfv2_self_if_ip_address:146.138.207.170',
            'huawei_hw_ospfv2_self_if_name:but quaintly quaintly kept Jaded',
            'huawei_hw_ospfv2_self_router_id:162.72.182.24',
        ],
        [
            'huawei_hw_ospfv2_nbr_gr_status:normal',
            'huawei_hw_ospfv2_nbr_if_backup_designated_router:53.213.159.224',
            'huawei_hw_ospfv2_nbr_if_designated_router:246.21.44.22',
            'huawei_hw_ospfv2_nbr_mode:slave',
            'huawei_hw_ospfv2_nbr_state:loading',
            'huawei_hw_ospfv2_neighbor_router_id:247.138.57.169',
            'huawei_hw_ospfv2_self_if_ip_address:90.19.208.128',
            'huawei_hw_ospfv2_self_if_name:kept oxen acted Jaded',
            'huawei_hw_ospfv2_self_router_id:125.55.112.183',
        ],
        [
            'huawei_hw_ospfv2_nbr_gr_status:notsupport',
            'huawei_hw_ospfv2_nbr_if_backup_designated_router:172.219.171.223',
            'huawei_hw_ospfv2_nbr_if_designated_router:177.94.236.224',
            'huawei_hw_ospfv2_nbr_mode:master',
            'huawei_hw_ospfv2_nbr_state:loading',
            'huawei_hw_ospfv2_neighbor_router_id:144.138.234.234',
            'huawei_hw_ospfv2_self_if_ip_address:147.54.130.211',
            'huawei_hw_ospfv2_self_if_name:quaintly but their zombies but zombies',
            'huawei_hw_ospfv2_self_router_id:186.4.129.159',
        ],
        [
            'huawei_hw_ospfv2_nbr_gr_status:notsupport',
            'huawei_hw_ospfv2_nbr_if_backup_designated_router:180.4.54.232',
            'huawei_hw_ospfv2_nbr_if_designated_router:24.193.97.154',
            'huawei_hw_ospfv2_nbr_mode:slave',
            'huawei_hw_ospfv2_nbr_state:down',
            'huawei_hw_ospfv2_neighbor_router_id:252.167.100.108',
            'huawei_hw_ospfv2_self_if_ip_address:183.39.48.78',
            'huawei_hw_ospfv2_self_if_name:quaintly driving oxen kept acted kept but',
            'huawei_hw_ospfv2_self_router_id:174.83.140.32',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwOspfv2NbrDeadTimeLeft', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwOspfv2NbrPriority', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwOspfv2NbrUpTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['cpu:29'],
        ['cpu:8'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.huawei.hwAvgDuty1min', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mem:1'],
        ['mem:6'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwMemoryDevFree', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwMemoryDevSize', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'huawei Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'huawei.device.name',
        'profile': 'huawei',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2011.2.999',
        'vendor': 'huawei',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    assert_all_profile_metrics_and_tags_covered('huawei', aggregator)
