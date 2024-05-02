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


def test_e2e_profile_cisco_ironport_email(dd_agent_check):
    profile = 'cisco-ironport-email'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-ironport-email',
        'snmp_host:cisco-ironport-email.device.name',
        'device_hostname:cisco-ironport-email.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'ironport_cache_admin:forward Jaded Jaded oxen',
        'ironport_cache_software:but driving Jaded but kept but Jaded',
        'ironport_cache_version:acted driving their oxen kept forward',
        'ironport_http_ports:but Jaded oxen kept',
        'ironport_license_expiration:5',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheBwidthSavingNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheBwidthSpentNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheBwidthTotalNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheClientAccepts', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheClientErrors', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheClientIdleConns', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheClientMaxConns', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheClientReqDenials', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheClientRequests', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheClientTotalConns', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheCltReplyErrPct', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheDeniedNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheDeniedRespTimeNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheDuration', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheErrRespTimeNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheErrsNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheHitRespTimeNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheHitsNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheMeanByteHitRatio', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheMeanHitRatio', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheMeanHitRespTime', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheMeanMissRespTime', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheMeanRespTime', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheMissRespTimeNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheMissesNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheServerCloseIdleConns', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheServerConnsThresh', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheServerErrors', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheServerIdleConns', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheServerLimitIdleConns', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheServerRequests', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheServerSockets', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheServerTotalConns', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheThruputNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheTotalBandwidthSaving', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheTotalHttpReqs', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.cacheTotalRespTimeNow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.mailTransferThreads', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.oldestMessageAge', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.openFilesOrSockets', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.outstandingDNSRequests', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.pendingDNSRequests', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.perCentCPULoad', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.perCentDiskIOUtilization', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.perCentQueueUtilization', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.raidEvents', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ironport.workQueueMessages', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'ironport_power_supply_name:kept',
            'ironport_power_supply_redundancy:power_supply_redundancy_lost',
            'ironport_power_supply_status:power_supply_not_installed',
        ],
        [
            'ironport_power_supply_name:oxen their oxen oxen zombies driving quaintly their',
            'ironport_power_supply_redundancy:power_supply_redundancy_ok',
            'ironport_power_supply_status:power_supply_no_ac',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ironport.powerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ironport_temperature_name:kept'],
        ['ironport_temperature_name:oxen kept oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ironport.degreesCelsius', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['ironport_fan_name:driving Jaded Jaded quaintly quaintly forward Jaded driving'],
        ['ironport_fan_name:zombies kept quaintly quaintly kept Jaded zombies but Jaded'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ironport.fanRPMs', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ironport_key_description:their kept driving but kept driving kept oxen', 'ironport_key_is_perpetual:true'],
        ['ironport_key_description:zombies oxen', 'ironport_key_is_perpetual:false'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ironport.keySecondsUntilExpire', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['ironport_update_service_name:acted'],
        ['ironport_update_service_name:their acted but'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ironport.updateFailures', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.ironport.updates', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'ironport_raid_id:but Jaded',
            'ironport_raid_last_error:their their oxen but Jaded their driving kept',
            'ironport_raid_status:drive_failure',
        ],
        [
            'ironport_raid_id:zombies zombies their Jaded oxen',
            'ironport_raid_last_error:but quaintly their',
            'ironport_raid_status:drive_healthy',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ironport.raid', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'cisco-ironport-email Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cisco-ironport-email.device.name',
        'profile': 'cisco-ironport-email',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.15497.1.2',
        'vendor': 'cisco',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
