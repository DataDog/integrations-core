# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_host_resources_base,
    assert_extend_generic_if,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_ibm_lenovo_server(dd_agent_check):
    config = create_e2e_core_test_config('ibm-lenovo-server')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:ibm-lenovo-server',
        'snmp_host:ibm-lenovo-server.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + [
        'ibm_machine_level_product_name:Jaded acted their but acted kept driving ' 'Jaded Jaded',
        'ibm_machine_level_serial_number:driving quaintly quaintly but driving',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['ibm_temp_descr:acted oxen oxen their but', 'ibm_temp_health_status:but quaintly forward'],
        ['ibm_temp_descr:quaintly acted kept', 'ibm_temp_health_status:acted quaintly acted zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.tempReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ibm_volt_descr:kept Jaded quaintly kept their', 'ibm_volt_health_status:quaintly Jaded zombies oxen'],
        ['ibm_volt_descr:zombies acted their their', 'ibm_volt_health_status:acted forward kept forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.voltReading', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ibm_fan_descr:kept but quaintly acted Jaded', 'ibm_fan_health_status:acted acted forward acted'],
        ['ibm_fan_descr:their but quaintly oxen', 'ibm_fan_health_status:kept'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.fanSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'ibm_system_health_summary_description:acted Jaded their quaintly zombies but oxen',
            'ibm_system_health_summary_severity:Jaded',
        ],
        [
            'ibm_system_health_summary_description:driving driving acted but',
            'ibm_system_health_summary_severity:oxen Jaded',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ibm.systemHealthSummary', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'ibm_cpu_vpd_description:Jaded driving',
            'ibm_cpu_vpd_health_status:driving driving their kept quaintly driving their but kept',
        ],
        ['ibm_cpu_vpd_description:their quaintly', 'ibm_cpu_vpd_health_status:acted driving kept zombies driving kept'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.systemCPUVpd', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'ibm_memory_health_status:but acted',
            'ibm_memory_vpd_description:quaintly acted forward quaintly their zombies',
        ],
        [
            'ibm_memory_health_status:their kept quaintly Jaded kept',
            'ibm_memory_vpd_description:their Jaded acted their their',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.systemMemoryVpd', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ibm_power_fru_name:driving driving', 'ibm_power_health_status:but forward but their but'],
        ['ibm_power_fru_name:forward', 'ibm_power_health_status:Jaded'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.power', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ibm_disk_fru_name:acted Jaded', 'ibm_disk_health_status:driving driving zombies Jaded'],
        ['ibm_disk_fru_name:oxen', 'ibm_disk_health_status:forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ibm.disk', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

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
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
