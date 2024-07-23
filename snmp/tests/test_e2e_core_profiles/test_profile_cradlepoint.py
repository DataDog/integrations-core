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


def test_e2e_profile_cradlepoint(dd_agent_check):
    profile = 'cradlepoint'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cradlepoint',
        'snmp_host:cradlepoint.device.name',
        'device_hostname:cradlepoint.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'cradlepoint_mdm_apn:quaintly',
            'cradlepoint_mdm_descr:acted but their kept',
            'cradlepoint_mdm_homecarrier:zombies kept zombies but zombies',
            'cradlepoint_mdm_port:driving acted their kept acted their',
            'cradlepoint_mdm_rfband:zombies but forward acted zombies acted their driving',
            'cradlepoint_mdm_rfchannel:acted their but acted',
            'cradlepoint_mdm_roam:2',
            'cradlepoint_mdm_status:disconnected',
        ],
        [
            'cradlepoint_mdm_apn:quaintly forward driving acted',
            'cradlepoint_mdm_descr:driving but Jaded oxen their but oxen forward quaintly',
            'cradlepoint_mdm_homecarrier:driving acted',
            'cradlepoint_mdm_port:forward zombies their',
            'cradlepoint_mdm_rfband:forward acted zombies Jaded Jaded oxen',
            'cradlepoint_mdm_rfchannel:their oxen Jaded but',
            'cradlepoint_mdm_roam:0',
            'cradlepoint_mdm_status:ready',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cradlepoint.mdmCINR', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cradlepoint.mdmECIO', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cradlepoint.mdmRSRP', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cradlepoint.mdmRSRQ', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cradlepoint.mdmSINR', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cradlepoint.mdmSignalStrength', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'cradlepoint Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cradlepoint.device.name',
        'profile': 'cradlepoint',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.20992.2.46',
        'vendor': 'cradlepoint',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
