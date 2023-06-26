# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_aruba_clearpass(dd_agent_check):
    config = create_e2e_core_test_config('aruba-clearpass')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:aruba-clearpass',
        'snmp_host:aruba-clearpass.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cppmSystemDiskSpaceFree', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cppmSystemDiskSpaceTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cppmSystemMemoryFree', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cppmSystemMemoryTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.radAuthRequestTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radServerCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radServerCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radServerCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['rad_auth_source_name:Jaded kept oxen their zombies driving forward'],
         ['rad_auth_source_name:acted quaintly zombies but Jaded acted but'],
         ['rad_auth_source_name:but forward forward kept but forward forward oxen'],
         ['rad_auth_source_name:but kept zombies but kept kept zombies zombies oxen'],
         ['rad_auth_source_name:driving acted but acted zombies their their driving'],
         ['rad_auth_source_name:forward but driving their'],
         ['rad_auth_source_name:kept oxen driving their kept but but'],
         ['rad_auth_source_name:oxen'],
         ['rad_auth_source_name:quaintly driving but quaintly'],
         ['rad_auth_source_name:quaintly driving driving driving'],
         ['rad_auth_source_name:quaintly kept Jaded forward'],
         ['rad_auth_source_name:their their forward but but driving'],
         ['rad_auth_source_name:zombies acted forward quaintly their'],
         ['rad_auth_source_name:zombies kept forward but'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.radAuthCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radAuthCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radAuthCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.radAuthCounterTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dailyFailedAuthCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.dailySuccessAuthCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.dailyTotalAuthCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAuditPolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAuditPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAuthCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAuthCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAuthCounterTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psEnforcementPolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psEnforcementPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psPosturePolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psPosturePolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psRestrictionPolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psRestrictionPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psRolemappingPolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psRolemappingPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psServicePolicyEvalCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psServicePolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psSessionlogTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['ps_autz_source_name:Jaded driving oxen'],
         ['ps_autz_source_name:driving but their quaintly quaintly quaintly their but oxen'],
         ['ps_autz_source_name:forward quaintly quaintly'],
         ['ps_autz_source_name:kept forward their zombies oxen driving driving but'],
         ['ps_autz_source_name:oxen driving acted kept Jaded driving kept oxen'],
         ['ps_autz_source_name:quaintly Jaded kept'],
         ['ps_autz_source_name:their Jaded acted driving acted quaintly'],
         ['ps_autz_source_name:their acted acted zombies but acted driving'],
         ['ps_autz_source_name:their but but acted kept'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.psAutzCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAutzCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAutzCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.psAutzCounterTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tacAuthCounterAuthTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAuthCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAuthCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAuthCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAuthCounterTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacPolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacServicePolicyEvalTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tacAutzCounterCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAutzCounterFailure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAutzCounterSuccess', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tacAutzCounterTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['nw_app_name:driving Jaded driving oxen forward quaintly their kept kept'],
         ['nw_app_name:driving forward kept but'],
         ['nw_app_name:forward'],
         ['nw_app_name:forward oxen quaintly but Jaded forward quaintly'],
         ['nw_app_name:kept acted acted oxen'],
         ['nw_app_name:oxen'],
         ['nw_app_name:quaintly oxen driving but their zombies zombies acted'],
         ['nw_app_name:quaintly quaintly'],
         ['nw_app_name:their kept forward acted acted'],
         ['nw_app_name:their zombies acted their oxen'],
         ['nw_app_name:zombies their'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.nwAppPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nwTrafficTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)


    aggregator.assert_all_metrics_covered()

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
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)
