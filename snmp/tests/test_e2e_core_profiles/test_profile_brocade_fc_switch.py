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


def test_e2e_profile_brocade_fc_switch(dd_agent_check):
    profile = 'brocade-fc-switch'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:brocade-fc-switch',
        'snmp_host:brocade-fc-switch.device.name',
        'device_hostname:brocade-fc-switch.device.name',
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
    tag_rows = [
        [
            'fc_fe_module_index:40140',
            'fc_fx_port_admin_mode:f_port',
            'fc_fx_port_index:50904',
            'fc_fx_port_oper_mode:f_port',
        ],
        [
            'fc_fe_module_index:48039',
            'fc_fx_port_admin_mode:fl_port',
            'fc_fx_port_index:17014',
            'fc_fx_port_oper_mode:f_port',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fcFxPortStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'fc_fe_module_index:28355',
            'fc_fx_port_index:44487',
            'fc_fx_port_phys_admin_status:offline',
            'fc_fx_port_phys_oper_status:online',
        ],
        [
            'fc_fe_module_index:36669',
            'fc_fx_port_index:26368',
            'fc_fx_port_phys_admin_status:testing',
            'fc_fx_port_phys_oper_status:online',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fcFxPortPhys', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'sw_fc_port_name:Jaded driving their zombies forward acted quaintly oxen',
            'sw_fc_port_specifier:driving driving kept their but Jaded zombies forward quaintly',
        ],
        [
            'sw_fc_port_name:Jaded forward forward',
            'sw_fc_port_specifier:oxen quaintly forward driving quaintly kept zombies',
        ],
        ['sw_fc_port_name:zombies kept driving zombies kept forward acted Jaded', 'sw_fc_port_specifier:driving acted'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.swFCPortC3Discards', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortNoTxCredits', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRcTruncs', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxBadEofs', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxBadOs', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxC2Frames', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxC3Frames', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxCrcs', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxEncInFrs', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxEncOutFrs', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxFrames', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxLCs', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortRxTooLongs', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortTooManyRdys', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.swFCPortTxFrames', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'brocade-fc-switch Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'brocade-fc-switch.device.name',
        'profile': 'brocade-fc-switch',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.1588.2.1.1.32',
        'vendor': 'brocade',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
