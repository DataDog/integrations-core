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


def test_e2e_profile_sinetica_eagle_i(dd_agent_check):
    config = create_e2e_core_test_config('sinetica-eagle-i')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:sinetica-eagle-i',
        'snmp_host:sinetica-eagle-i.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + [
        'hawk_i2_inv_fw_revision:oxen Jaded',
        'hawk_i2_inv_hw_revision:acted',
        'hawk_i2_inv_serial_num:Jaded',
        'hawk_i2_ip_temp_scale_flag:1',
    ]

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['hawk_i2_ip_tha_locn:but', 'hawk_i2_ip_tha_name:their forward'],
        ['hawk_i2_ip_tha_locn:oxen', 'hawk_i2_ip_tha_name:forward driving'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.hawk.i2.ipTHAValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'hawk_i2_ip_cont_curr_state:open',
            'hawk_i2_ip_cont_locn:kept',
            'hawk_i2_ip_cont_name:driving',
            'hawk_i2_ip_cont_norm_state:1',
        ],
        [
            'hawk_i2_ip_cont_curr_state:open',
            'hawk_i2_ip_cont_locn:kept',
            'hawk_i2_ip_cont_name:driving zombies',
            'hawk_i2_ip_cont_norm_state:1',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.hawk.i2.ipCont', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'hawk_i2_op_control_state:deactivate',
            'hawk_i2_op_curr_state:on',
            'hawk_i2_op_locn:kept',
            'hawk_i2_op_name:driving',
            'hawk_i2_op_norm_state:off',
        ],
        [
            'hawk_i2_op_control_state:logic',
            'hawk_i2_op_curr_state:on',
            'hawk_i2_op_locn:oxen',
            'hawk_i2_op_name:quaintly',
            'hawk_i2_op_norm_state:off',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.hawk.i2.op', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    aggregator.assert_metric('snmp.hawk.i2.pduRMSAmpsValue', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hawk.i2.pduRMSVoltsValue', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hawk.i2.pduTotalEnergyValue', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'sinetica-eagle-i Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'sinetica-eagle-i.device.name',
        'profile': 'sinetica-eagle-i',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.3711.24',
        'vendor': 'sinetica',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
