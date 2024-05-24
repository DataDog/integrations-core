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
    assert_extend_generic_entity_sensor,
    assert_extend_generic_if,
    assert_extend_generic_ospf,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_avaya_media_gateway(dd_agent_check):
    profile = 'avaya-media-gateway'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:avaya-media-gateway',
        'snmp_host:avaya-media-gateway.device.name',
        'device_hostname:avaya-media-gateway.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_id:default:' + ip_address,
        'device_ip:' + ip_address,
    ] + [
        'avaya_cmg_active_controller_address:112.163.176.135',
        'avaya_cmg_hw_type:avaya_g250-a14',
        'avaya_cmg_model_number:zombies acted',
        'avaya_cmg_serial_number:their',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ospf(aggregator, common_tags)
    assert_extend_generic_entity_sensor(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.avaya.cmgCurrent802Vlan', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.avaya.cmgH248LinkErrorCode', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.avaya.cmgLocalSig802Priority', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.avaya.cmgLocalSigDscp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.avaya.cmgRemoteSig802Priority', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.avaya.cmgRemoteSigDscp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'avaya_av_ent_phy_ch_fru_fault:mulfunction',
            'avaya_av_ent_phy_ch_fru_oper_stat:fault',
            'avaya_ent_physical_index:29',
        ],
        ['avaya_av_ent_phy_ch_fru_fault:none', 'avaya_av_ent_phy_ch_fru_oper_stat:ok', 'avaya_ent_physical_index:21'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.avaya.avEntPhyChFru', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'avaya_cmg_voip_admin_state:busy-out',
            'avaya_cmg_voip_current_ip_address:10.199.41.206',
            'avaya_cmg_voip_dsp_status:fault',
            'avaya_cmg_voip_hyperactivity:hyperactive',
        ],
        [
            'avaya_cmg_voip_admin_state:busy-out',
            'avaya_cmg_voip_current_ip_address:127.208.248.67',
            'avaya_cmg_voip_dsp_status:in_use',
            'avaya_cmg_voip_hyperactivity:hyperactive',
        ],
        [
            'avaya_cmg_voip_admin_state:camp-on',
            'avaya_cmg_voip_current_ip_address:18.213.33.254',
            'avaya_cmg_voip_dsp_status:fault',
            'avaya_cmg_voip_hyperactivity:normal',
        ],
        [
            'avaya_cmg_voip_admin_state:camp-on',
            'avaya_cmg_voip_current_ip_address:248.128.11.156',
            'avaya_cmg_voip_dsp_status:in_use',
            'avaya_cmg_voip_hyperactivity:normal',
        ],
        [
            'avaya_cmg_voip_admin_state:release',
            'avaya_cmg_voip_current_ip_address:192.247.245.247',
            'avaya_cmg_voip_dsp_status:in_use',
            'avaya_cmg_voip_hyperactivity:normal',
        ],
        [
            'avaya_cmg_voip_admin_state:release',
            'avaya_cmg_voip_current_ip_address:251.46.128.231',
            'avaya_cmg_voip_dsp_status:in_use',
            'avaya_cmg_voip_hyperactivity:normal',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.avaya.cmgVoipAverageOccupancy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.avaya.cmgVoipChannelsInUse', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.avaya.cmgVoipTotalChannels', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'avaya_cmg_dsp_core_admin_state:busy-out',
            'avaya_cmg_dsp_core_demand_test_result:error_code1',
            'avaya_cmg_dsp_core_status:fault',
        ],
        [
            'avaya_cmg_dsp_core_admin_state:busy-out',
            'avaya_cmg_dsp_core_demand_test_result:error_code3',
            'avaya_cmg_dsp_core_status:in_use',
        ],
        [
            'avaya_cmg_dsp_core_admin_state:busy-out',
            'avaya_cmg_dsp_core_demand_test_result:error_code5',
            'avaya_cmg_dsp_core_status:fault',
        ],
        [
            'avaya_cmg_dsp_core_admin_state:camp-on',
            'avaya_cmg_dsp_core_demand_test_result:error_code2',
            'avaya_cmg_dsp_core_status:idle',
        ],
        [
            'avaya_cmg_dsp_core_admin_state:release',
            'avaya_cmg_dsp_core_demand_test_result:error_code2',
            'avaya_cmg_dsp_core_status:fault',
        ],
        [
            'avaya_cmg_dsp_core_admin_state:release',
            'avaya_cmg_dsp_core_demand_test_result:error_code4',
            'avaya_cmg_dsp_core_status:in_use',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.avaya.cmgDSPCoreChannelsInUse', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.avaya.cmgDSPCoreTotalChannels', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'avaya-media-gateway Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'avaya-media-gateway.device.name',
        'profile': 'avaya-media-gateway',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.6889.1.45.103.41',
        'vendor': 'avaya',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
