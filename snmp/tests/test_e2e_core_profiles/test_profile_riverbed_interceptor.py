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
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_riverbed_interceptor(dd_agent_check):
    config = create_e2e_core_test_config('riverbed-interceptor')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:riverbed-interceptor',
        'snmp_host:riverbed-interceptor.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'reverbed_interceptor_model:kept zombies Jaded but driving their but',
        'reverbed_interceptor_serial_number:but zombies quaintly acted but',
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ifBandwidthInUsage.rate')
    aggregator.assert_metric('snmp.ifBandwidthOutUsage.rate')
    aggregator.assert_metric('snmp.ifHCInBroadcastPkts')
    aggregator.assert_metric('snmp.ifHCInMulticastPkts')
    aggregator.assert_metric('snmp.ifHCInOctets')
    aggregator.assert_metric('snmp.ifHCInOctets.rate')
    aggregator.assert_metric('snmp.ifHCInUcastPkts')
    aggregator.assert_metric('snmp.ifHCOutBroadcastPkts')
    aggregator.assert_metric('snmp.ifHCOutMulticastPkts')
    aggregator.assert_metric('snmp.ifHCOutOctets')
    aggregator.assert_metric('snmp.ifHCOutOctets.rate')
    aggregator.assert_metric('snmp.ifHCOutUcastPkts')
    aggregator.assert_metric('snmp.ifHighSpeed')
    aggregator.assert_metric('snmp.ifInSpeed')
    aggregator.assert_metric('snmp.ifOutSpeed')
    aggregator.assert_metric('snmp.reverbed.interceptor.proc')
    aggregator.assert_metric('snmp.reverbed.interceptor.neighborConnectionCount')

    # --- TEST METADATA ---
    device = {
        'description': 'riverbed-interceptor Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'riverbed-interceptor.device.name',
        'profile': 'riverbed-interceptor',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.17163.1.3',
        'vendor': 'riverbed',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
