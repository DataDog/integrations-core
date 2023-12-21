# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile__generic_if(dd_agent_check):
    config = create_e2e_core_test_config('_generic-if')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:_generic-if',
        'snmp_host:_generic-if.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.ifNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['interface_index:15'],
        ['interface_index:19'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ifInDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifInErrors', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifOutDiscards', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifOutErrors', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['interface_index:15'],
        ['interface_index:19'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ifAdminStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifOperStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'interface:Jaded acted oxen forward but',
            'interface_alias:zombies zombies their oxen acted zombies their',
            'interface_index:11',
        ],
        [
            'interface:quaintly driving their acted quaintly',
            'interface_alias:Jaded kept oxen Jaded driving oxen driving their kept',
            'interface_index:31',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ifHCInBroadcastPkts', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifHCInMulticastPkts', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifHCInUcastPkts', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifHCOutBroadcastPkts', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifHCOutMulticastPkts', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifHCOutUcastPkts', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    tag_rows = [
        [
            'interface:Jaded acted oxen forward but',
            'interface_alias:zombies zombies their oxen acted zombies their',
            'interface_index:11',
        ],
        [
            'interface:quaintly driving their acted quaintly',
            'interface_alias:Jaded kept oxen Jaded driving oxen driving their kept',
            'interface_index:31',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ifHCInOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ifHCOutOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'interface:Jaded acted oxen forward but',
            'interface_alias:zombies zombies their oxen acted zombies their',
            'interface_index:11',
        ],
        [
            'interface:quaintly driving their acted quaintly',
            'interface_alias:Jaded kept oxen Jaded driving oxen driving their kept',
            'interface_index:31',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ifHighSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'if_stack_higher_layer:Jaded acted oxen forward but',
            'if_stack_lower_layer:quaintly driving their acted quaintly',
            'if_stack_status:not_ready',
        ],
        ['if_stack_higher_layer:Jaded acted oxen forward but', 'if_stack_status:not_in_service'],
        ['if_stack_lower_layer:Jaded acted oxen forward but', 'if_stack_status:active'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ifStack', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': '_generic-if Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_generic-if.device.name',
        'profile': '_generic-if',
        'status': 1,
        'sys_object_id': '1.2.3.20231221',
        'vendor': '_generic',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
