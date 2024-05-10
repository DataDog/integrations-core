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


def test_e2e_profile_mcafee_web_gateway(dd_agent_check):
    profile = 'mcafee-web-gateway'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:mcafee-web-gateway',
        'snmp_host:mcafee-web-gateway.device.name',
        'device_hostname:mcafee-web-gateway.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'mcafee_mwg_k_build_number:9',
        'mcafee_mwg_k_company_name:driving zombies kept',
        'mcafee_mwg_k_custom_version:2',
        'mcafee_mwg_k_hotfix_version:22',
        'mcafee_mwg_k_major_version:27',
        'mcafee_mwg_k_micro_version:6',
        'mcafee_mwg_k_minor_version:18',
        'mcafee_mwg_k_product_name:driving acted quaintly forward forward',
        'mcafee_mwg_k_product_version:forward zombies acted quaintly kept kept',
        'mcafee_mwg_k_revision:forward acted',
        'mcafee_mwg_p_am_engine_version:quaintly',
        'mcafee_mwg_p_am_proactive_version:Jaded',
        'mcafee_mwg_p_mfe_engine_version:Jaded their',
        'mcafee_mwg_p_mfedat_version:forward',
        'mcafee_mwg_p_tsdb_version:oxen',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stBlockedByAntiMalware', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stBlockedByMediaFilter', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stBlockedByURLFilter', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stCategories', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stClientCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stConnectedSockets', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stConnectionsBlocked', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stConnectionsLegitimate', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stFtpBytesFromClient', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stFtpBytesFromServer', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stFtpBytesToClient', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stFtpBytesToServer', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stFtpTraffic', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpBytesFromClient', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpBytesFromServer', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpBytesToClient', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpBytesToServer', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpRequests', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpTraffic', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpsBytesFromClient', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpsBytesFromServer', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpsBytesToClient', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpsBytesToServer', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpsRequests', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stHttpsTraffic', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stMalwareDetected', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stMimeType', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.mcafee.mwg.stResolveHostViaDNS', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric(
        'snmp.mcafee.mwg.stTimeConsumedByRuleEngine', metric_type=aggregator.COUNT, tags=common_tags
    )
    aggregator.assert_metric('snmp.mcafee.mwg.stTimeForTransaction', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['mcafee_mwg_st_category_name:driving their forward'],
        ['mcafee_mwg_st_category_name:kept forward zombies their Jaded oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.mcafee.mwg.stCategoryCount', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'mcafee-web-gateway Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'mcafee-web-gateway.device.name',
        'profile': 'mcafee-web-gateway',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.1230.2.7.1.1',
        'vendor': 'mcafee',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
