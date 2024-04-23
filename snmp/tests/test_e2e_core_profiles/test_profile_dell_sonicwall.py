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


def test_e2e_profile_dell_sonicwall(dd_agent_check):
    profile = 'dell-sonicwall'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dell-sonicwall',
        'snmp_host:dell-sonicwall.device.name',
        'device_hostname:dell-sonicwall.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sonicCurrentConnCacheEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sonicDpiSslConnCountCur', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sonicDpiSslConnCountHighWater', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sonicDpiSslConnCountMax', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sonicMaxConnCacheEntries', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sonicNatTranslationCount', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'sonic_sa_stat_dst_addr_begin:235.185.120.197',
            'sonic_sa_stat_dst_addr_end:248.89.108.190',
            'sonic_sa_stat_peer_gateway:47.169.129.76',
            'sonic_sa_stat_src_addr_begin:57.166.34.35',
            'sonic_sa_stat_src_addr_end:167.235.34.58',
            'sonic_sa_stat_create_time:Jaded driving acted quaintly',
            'sonic_sa_stat_user_name:but forward zombies but acted kept zombies Jaded',
        ],
        [
            'sonic_sa_stat_dst_addr_begin:60.247.243.34',
            'sonic_sa_stat_dst_addr_end:157.82.31.152',
            'sonic_sa_stat_peer_gateway:158.64.168.219',
            'sonic_sa_stat_src_addr_begin:140.76.154.238',
            'sonic_sa_stat_src_addr_end:240.205.65.247',
            'sonic_sa_stat_create_time:driving quaintly oxen Jaded forward',
            'sonic_sa_stat_user_name:kept but',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sonicSAStatDecryptByteCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sonicSAStatDecryptPktCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sonicSAStatEncryptByteCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sonicSAStatEncryptPktCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sonicSAStatInFragPktCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sonicSAStatOutFragPktCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'dell-sonicwall Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'model': 'TZ 400',
        'name': 'dell-sonicwall.device.name',
        'profile': 'dell-sonicwall',
        'serial_number': 'S16195058',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.8741.1',
        'vendor': 'dell',
        'version': '01972WA81B1D',
        'device_type': 'firewall',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
