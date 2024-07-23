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
    assert_extend_generic_bgp4,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_nec_univerge(dd_agent_check):
    profile = 'nec-univerge'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:nec-univerge',
        'snmp_host:nec-univerge.device.name',
        'device_hostname:nec-univerge.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_bgp4(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.picoCelsius', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.picoFahrenheit', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.picoVoltage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalActiveTunnels', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalAuthFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalDecryptFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalHashValidFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalInNotifys', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalInP1SaDelRequests', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalInP2ExchgInvalids', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalInP2ExchgRejects', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalInP2Exchgs', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalInP2SaDelRequests', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalInitTunnelFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalInitTunnels', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalOutNotifys', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalOutP1SaDelRequests', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalOutP2ExchgInvalids', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalOutP2ExchgRejects', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalOutP2Exchgs', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalOutP2SaDelRequests', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalRespTunnelFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pikeGlobalRespTunnels', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalActiveTunnels', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalInAuthFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalInAuths', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalInDecryptFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalInDecrypts', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalInDrops', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalInOctets', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalInPkts', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalInReplayDrops', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalNoSaFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalOutAuthFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalOutAuths', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalOutDrops', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalOutEncryptFails', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalOutEncrypts', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalOutOctets', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nec.pipSecGlobalOutPkts', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'nec-univerge Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'nec-univerge.device.name',
        'profile': 'nec-univerge',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.119.1.84.18',
        'vendor': 'nec',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
