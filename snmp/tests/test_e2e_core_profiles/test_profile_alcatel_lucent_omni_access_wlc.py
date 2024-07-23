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


def test_e2e_profile_alcatel_lucent_omni_access_wlc(dd_agent_check):
    profile = 'alcatel-lucent-omni-access-wlc'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:alcatel-lucent-omni-access-wlc',
        'snmp_host:alcatel-lucent-omni-access-wlc.device.name',
        'device_hostname:alcatel-lucent-omni-access-wlc.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'wlsx_model_name:quaintly Jaded oxen oxen',
        'wlsx_switch_license_serial_number:quaintly oxen their',
        'wlsx_switch_role:standbymaster',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.wlsxSwitchTotalNumAccessPoints', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.wlsxSwitchTotalNumStationsAssociated', metric_type=aggregator.GAUGE, tags=common_tags
    )
    tag_rows = [
        ['sys_x_processor_descr:Jaded acted quaintly their forward Jaded forward oxen Jaded', 'cpu:4'],
        ['sys_x_processor_descr:zombies zombies their acted Jaded', "cpu:27"],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['sys_x_storage_name:acted oxen oxen their quaintly', 'sys_x_storage_type:flash_memory'],
        ['sys_x_storage_name:oxen', 'sys_x_storage_type:flash_memory'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sysXStorageSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.sysXStorageUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mem:1'],
        ['mem:24'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'alcatel-lucent-omni-access-wlc Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'alcatel-lucent-omni-access-wlc.device.name',
        'profile': 'alcatel-lucent-omni-access-wlc',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.6486.800.1.1.2.2.2.1.1.4',
        'vendor': 'alcatel-lucent',
        'device_type': 'wlc',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
