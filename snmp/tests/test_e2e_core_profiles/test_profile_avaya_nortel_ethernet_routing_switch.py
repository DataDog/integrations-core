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


def test_e2e_profile_avaya_nortel_ethernet_routing_switch(dd_agent_check):
    profile = 'avaya-nortel-ethernet-routing-switch'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:avaya-nortel-ethernet-routing-switch',
        'snmp_host:avaya-nortel-ethernet-routing-switch.device.name',
        'device_hostname:avaya-nortel-ethernet-routing-switch.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + ['avaya_s5_chas_ser_num:oxen', 'avaya_s5_chas_ver:Jaded driving']

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.avaya.s5ChasTmpSnrTmpValue', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'avaya_s5_chas_com_admin_state:reset',
            'avaya_s5_chas_com_descr:but Jaded driving Jaded acted oxen their forward but',
            'avaya_s5_chas_com_oper_state:warning',
        ],
        ['avaya_s5_chas_com_admin_state:reset', 'avaya_s5_chas_com_descr:oxen', 'avaya_s5_chas_com_oper_state:warning'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.avaya.s5ChasCom', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'avaya-nortel-ethernet-routing-switch Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'avaya-nortel-ethernet-routing-switch.device.name',
        'profile': 'avaya-nortel-ethernet-routing-switch',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.45.3.71.10',
        'vendor': 'avaya',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
