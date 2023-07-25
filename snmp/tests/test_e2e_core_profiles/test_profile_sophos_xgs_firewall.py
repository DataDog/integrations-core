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


def test_e2e_profile_sophos_xgs_firewall(dd_agent_check):
    config = create_e2e_core_test_config('sophos-xgs-firewall')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:sophos-xgs-firewall',
        'snmp_host:sophos-xgs-firewall.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + ['sfos_device_fw_version:but but zombies oxen forward',
 'sfos_device_type:their forward their but oxen',
 'sfos_ips_version:zombies but zombies but quaintly acted their']

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosBaseFWLicExpiryDate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosCentralOrchestrationLicExpiryDate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosDiskCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosDiskPercentUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosEnhancedPlusLicExpiryDate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosEnhancedSupportLicExpiryDate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosFTPHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosHTTPHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosImapHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosLiveUsersCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosMailProtectionLicExpiryDate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosNetProtectionLicExpiryDate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosPOP3Hits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosSandstromLicExpiryDate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosSmtpHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosSwapCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosSwapPercentUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosWebProtectionLicExpiryDate', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosWebServerProtectionLicExpiryDate', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
         ['sfos_ip_sec_vpn_conn_des:kept kept', 'sfos_ip_sec_vpn_conn_name:oxen quaintly Jaded acted', 'sfos_ip_sec_vpn_conn_type:site_to_site', 'sfos_ip_sec_vpn_policy_name:quaintly quaintly forward Jaded acted forward but'],
         ['sfos_ip_sec_vpn_conn_des:oxen but acted but driving oxen their forward quaintly', 'sfos_ip_sec_vpn_conn_name:kept forward acted forward Jaded forward', 'sfos_ip_sec_vpn_conn_type:site_to_site', 'sfos_ip_sec_vpn_policy_name:quaintly Jaded but kept'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sfosIPSecVpnActiveTunnel', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.sfosIPSecVpnConnMode', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.sfosIPSecVpnLocalgwPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'sophos-xgs-firewall Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'sophos-xgs-firewall.device.name',
        'profile': 'sophos-xgs-firewall',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2604.5',
        'vendor': 'sophos',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
