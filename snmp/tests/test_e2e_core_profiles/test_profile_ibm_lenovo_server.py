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
    assert_extend_generic_host_resources_base,
    assert_extend_generic_if,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_ibm_lenovo_server(dd_agent_check):
    profile = 'ibm-lenovo-server'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:ibm-lenovo-server',
        'snmp_host:ibm-lenovo-server.device.name',
        'device_hostname:ibm-lenovo-server.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'ibm_imm_machine_level_product_name:Jaded acted their but acted kept driving ' 'Jaded Jaded',
        'ibm_imm_machine_level_serial_number:driving quaintly quaintly but driving',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['ibm_imm_temp_descr:acted oxen oxen their but', 'ibm_imm_temp_health_status:but quaintly forward'],
        ['ibm_imm_temp_descr:quaintly acted kept', 'ibm_imm_temp_health_status:acted quaintly acted zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.imm.tempReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ibm_imm_volt_descr:kept Jaded quaintly kept their', 'ibm_imm_volt_health_status:quaintly Jaded zombies oxen'],
        ['ibm_imm_volt_descr:zombies acted their their', 'ibm_imm_volt_health_status:acted forward kept forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.imm.voltReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ibm_imm_fan_descr:kept but quaintly acted Jaded', 'ibm_imm_fan_health_status:acted acted forward acted'],
        ['ibm_imm_fan_descr:their but quaintly oxen', 'ibm_imm_fan_health_status:kept'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.imm.fanSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'ibm_imm_system_health_summary_description:acted Jaded their quaintly zombies but oxen',
            'ibm_imm_system_health_summary_severity:Jaded',
        ],
        [
            'ibm_imm_system_health_summary_description:driving driving acted but',
            'ibm_imm_system_health_summary_severity:oxen Jaded',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ibm.imm.systemHealthSummary', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'ibm_imm_cpu_vpd_description:Jaded driving',
            'ibm_imm_cpu_vpd_health_status:driving driving their kept quaintly driving their but kept',
        ],
        [
            'ibm_imm_cpu_vpd_description:their quaintly',
            'ibm_imm_cpu_vpd_health_status:acted driving kept zombies driving kept',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.imm.systemCPUVpd', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'ibm_imm_memory_health_status:but acted',
            'ibm_imm_memory_vpd_description:quaintly acted forward quaintly their zombies',
        ],
        [
            'ibm_imm_memory_health_status:their kept quaintly Jaded kept',
            'ibm_imm_memory_vpd_description:their Jaded acted their their',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ibm.imm.systemMemoryVpd', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['ibm_imm_power_fru_name:driving driving', 'ibm_imm_power_health_status:but forward but their but'],
        ['ibm_imm_power_fru_name:forward', 'ibm_imm_power_health_status:Jaded'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.imm.power', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ibm_imm_disk_fru_name:acted Jaded', 'ibm_imm_disk_health_status:driving driving zombies Jaded'],
        ['ibm_imm_disk_fru_name:oxen', 'ibm_imm_disk_health_status:forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.imm.disk', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'ibm-lenovo-server Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'ibm-lenovo-server.device.name',
        'profile': 'ibm-lenovo-server',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2.3.51.3',
        'vendor': 'ibm',
        'device_type': 'server',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
