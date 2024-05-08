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
    assert_extend_generic_ospf,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_aruba_clearpass(dd_agent_check):
    profile = 'aruba-clearpass'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:aruba-clearpass',
        'snmp_host:aruba-clearpass.device.name',
        'device_hostname:aruba-clearpass.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'cppm_system_version:5.0.1',
        'cppm_cluster_node_type:Master',
        'cppm_zone_name:Default',
        'cppm_num_cluster_nodes:3',
        'cppm_nw_mgmt_port_ip_address:192.168.1.1',
        'cppm_nw_mgmt_port_mac_address:00:1b:2c:4d:5e:6f',
        'cppm_nw_data_port_ip_address:192.168.1.2',
        'cppm_nw_data_port_mac_address:00:1b:2c:4d:5e:7p',
        'cppm_system_num_cp_us:4',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ospf(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['cppm_system_hostname:acted Jaded'],
        ['cppm_system_hostname:acted quaintly'],
        ['cppm_system_hostname:but quaintly forward zombies forward their'],
        ['cppm_system_hostname:forward zombies zombies kept'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cppmSystemDiskSpaceFree', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cppmSystemDiskSpaceTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.cppmSystemMemoryFree', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cppmSystemMemoryTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['cppm_system_hostname:acted Jaded'],
        ['cppm_system_hostname:acted quaintly'],
        ['cppm_system_hostname:but quaintly forward zombies forward their'],
        ['cppm_system_hostname:forward zombies zombies kept'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.radAuthRequestTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radServerCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.radServerCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.radServerCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['rad_auth_source_name:Jaded but quaintly zombies quaintly driving oxen'],
        ['rad_auth_source_name:forward forward'],
        ['rad_auth_source_name:oxen but driving oxen Jaded but'],
        ['rad_auth_source_name:quaintly kept Jaded Jaded Jaded oxen quaintly oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.radAuthCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radAuthCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radAuthCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radAuthCounterTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['cppm_system_hostname:acted Jaded'],
        ['cppm_system_hostname:acted quaintly'],
        ['cppm_system_hostname:but quaintly forward zombies forward their'],
        ['cppm_system_hostname:forward zombies zombies kept'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dailyFailedAuthCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.dailySuccessAuthCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.dailyTotalAuthCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.psAuditPolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.psAuditPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAuthCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAuthCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAuthCounterTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.psEnforcementPolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.psEnforcementPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.psPosturePolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.psPosturePolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.psRestrictionPolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.psRestrictionPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.psRolemappingPolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.psRolemappingPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.psServicePolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.psServicePolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.psSessionlogTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ps_autz_source_name:but kept'],
        ['ps_autz_source_name:oxen quaintly driving their quaintly forward zombies oxen their'],
        ['ps_autz_source_name:quaintly Jaded their their quaintly kept but driving but'],
        ['ps_autz_source_name:their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.psAutzCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAutzCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAutzCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAutzCounterTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['cppm_system_hostname:acted Jaded'],
        ['cppm_system_hostname:acted quaintly'],
        ['cppm_system_hostname:but quaintly forward zombies forward their'],
        ['cppm_system_hostname:forward zombies zombies kept'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.tacAuthCounterAuthTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.tacAuthCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAuthCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAuthCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAuthCounterTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.tacServicePolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.tacAutzCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAutzCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAutzCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAutzCounterTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['nw_app_name:oxen Jaded Jaded forward oxen kept'],
        ['nw_app_name:oxen their their but their acted oxen Jaded'],
        ['nw_app_name:their forward Jaded kept zombies'],
        ['nw_app_name:their zombies driving but but'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.nwAppPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nwTrafficTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'aruba-clearpass Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'aruba-clearpass.device.name',
        'profile': 'aruba-clearpass',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.14823.1.6.1',
        'vendor': 'aruba',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
