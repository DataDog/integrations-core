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


def test_e2e_profile_avaya_cajun_switch(dd_agent_check):
    profile = 'avaya-cajun-switch'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:avaya-cajun-switch',
        'snmp_host:avaya-cajun-switch.device.name',
        'device_hostname:avaya-cajun-switch.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + ['avaya_gen_cpu_utilization_enable_monitoring:enabled']

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'avaya_gen_port_admin_status:enabled',
            'avaya_gen_port_classification:valuable',
            'avaya_gen_port_descr:Jaded acted',
            'avaya_gen_port_functionality:ro',
            'avaya_gen_port_id:19',
            'avaya_gen_port_name:driving',
            'avaya_gen_port_type:ro_rj45',
            'avaya_sc_eth_port_functional_status:ok',
            'avaya_sc_eth_port_mode:full_duplex_proprietary_fc',
            'avaya_sc_eth_port_speed:fast_ethernet',
        ],
        [
            'avaya_gen_port_admin_status:enabled',
            'avaya_gen_port_classification:valuable',
            'avaya_gen_port_descr:zombies zombies but',
            'avaya_gen_port_functionality:wan',
            'avaya_gen_port_id:8',
            'avaya_gen_port_name:Jaded',
            'avaya_gen_port_type:ro_d9',
            'avaya_sc_eth_port_functional_status:rsp_error',
            'avaya_sc_eth_port_mode:full_duplex_flow_control_isl',
            'avaya_sc_eth_port_speed:a155_mbps',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.avaya.genPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'avaya-cajun-switch Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'avaya-cajun-switch.device.name',
        'profile': 'avaya-cajun-switch',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.81.17.1.19',
        'vendor': 'avaya',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
