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


def test_e2e_profile_sophos_xgs_firewall(dd_agent_check):
    profile = 'sophos-xgs-firewall'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:sophos-xgs-firewall',
        'snmp_host:sophos-xgs-firewall.device.name',
        'device_hostname:sophos-xgs-firewall.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'sfos_device_fw_version:forward zombies zombies oxen their',
        'sfos_device_type:Jaded forward kept acted but quaintly but',
        'sfos_ips_version:forward but quaintly their',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosDiskCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosDiskPercentUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosFTPHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosHTTPHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosImapHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosLiveUsersCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosPOP3Hits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosSmtpHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sfosSwapCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sfosSwapPercentUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'sfos_ip_sec_vpn_conn_des:oxen but forward their',
            'sfos_ip_sec_vpn_conn_mode:forward Jaded oxen oxen their forward',
            'sfos_ip_sec_vpn_conn_name:kept Jaded',
            'sfos_ip_sec_vpn_conn_type:site-to-site',
            'sfos_ip_sec_vpn_localgw_port:quaintly driving forward forward kept their forward',
            'sfos_ip_sec_vpn_policy_name:driving oxen forward quaintly quaintly but but',
        ],
        [
            'sfos_ip_sec_vpn_conn_des:oxen zombies acted forward kept',
            'sfos_ip_sec_vpn_conn_mode:zombies zombies kept zombies',
            'sfos_ip_sec_vpn_conn_name:but oxen acted oxen',
            'sfos_ip_sec_vpn_conn_type:host-to-host',
            'sfos_ip_sec_vpn_localgw_port:acted kept zombies Jaded Jaded but Jaded',
            'sfos_ip_sec_vpn_policy_name:oxen forward',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sfosIPSecVpnActiveTunnel', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.sfosIPSecVpnTunnel', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

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
        'device_type': 'firewall',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
