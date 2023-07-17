# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_if,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_cisco_ise(dd_agent_check):
    config = create_e2e_core_test_config('cisco-ise')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-ise',
        'snmp_host:cisco-ise.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    # Examples:
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # Extended metrics from `_generic-host-resources-base.yaml`
    aggregator.assert_metric("snmp.hrSystemUptime", metric_type=aggregator.GAUGE, tags=common_tags)
    cpu_rows = ['0.0']
    for cpu_row in cpu_rows:
        aggregator.assert_metric(
            'snmp.hrProcessorLoad', metric_type=aggregator.GAUGE, tags=common_tags + ['processorid:' + cpu_row]
        )

    hr_mem_rows = [
        ['storagedesc:my-storage-descr'],
    ]
    for mem_row in hr_mem_rows:
        aggregator.assert_metric('snmp.hrStorageSize', metric_type=aggregator.GAUGE, tags=common_tags + mem_row)
        aggregator.assert_metric('snmp.hrStorageUsed', metric_type=aggregator.GAUGE, tags=common_tags + mem_row)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'cisco-ise Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cisco-ise.device.name',
        'profile': 'cisco-ise',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.2785',
        'vendor': 'cisco',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
