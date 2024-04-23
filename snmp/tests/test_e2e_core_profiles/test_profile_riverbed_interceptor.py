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


def test_e2e_profile_riverbed_interceptor(dd_agent_check):
    profile = 'riverbed-interceptor'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:riverbed-interceptor',
        'snmp_host:riverbed-interceptor.device.name',
        'device_hostname:riverbed-interceptor.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'riverbed_interceptor_model:kept zombies Jaded but driving their but',
        'riverbed_interceptor_serial_number:but zombies quaintly acted but',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'riverbed_interceptor_proc_name:but acted Jaded but zombies their but',
            'riverbed_interceptor_proc_status:acted kept their Jaded Jaded driving Jaded acted',
        ],
        [
            'riverbed_interceptor_proc_name:forward zombies',
            'riverbed_interceptor_proc_status:their driving oxen acted oxen but acted',
        ],
        [
            'riverbed_interceptor_proc_name:oxen their oxen acted quaintly their oxen',
            'riverbed_interceptor_proc_status:driving quaintly zombies but',
        ],
        [
            'riverbed_interceptor_proc_name:quaintly quaintly acted kept',
            'riverbed_interceptor_proc_status:acted driving acted Jaded oxen',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.riverbed.interceptor.proc', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['riverbed_interceptor_neighbor_name:acted zombies their quaintly Jaded forward'],
        ['riverbed_interceptor_neighbor_name:driving'],
        ['riverbed_interceptor_neighbor_name:forward acted quaintly but oxen oxen their acted Jaded'],
        ['riverbed_interceptor_neighbor_name:oxen acted but'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.riverbed.interceptor.neighborConnectionCount',
            metric_type=aggregator.GAUGE,
            tags=common_tags + tag_row,
        )

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
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
