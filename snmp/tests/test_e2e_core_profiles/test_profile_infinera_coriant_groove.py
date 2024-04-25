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


def test_e2e_profile_infinera_coriant_groove(dd_agent_check):
    profile = 'infinera-coriant-groove'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:infinera-coriant-groove',
        'snmp_host:infinera-coriant-groove.device.name',
        'device_hostname:infinera-coriant-groove.device.name',
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
            'coriant_groove_shelf_admin_status:up',
            'coriant_groove_shelf_alias_name:driving their acted their',
            'coriant_groove_shelf_location:oxen but zombies kept acted oxen kept',
            'coriant_groove_shelf_oper_status:down',
            'coriant_groove_shelf_avail_status:shutdown',
        ],
        [
            'coriant_groove_shelf_admin_status:up_no_alm',
            'coriant_groove_shelf_alias_name:Jaded kept oxen driving',
            'coriant_groove_shelf_location:forward but zombies forward',
            'coriant_groove_shelf_oper_status:down',
            'coriant_groove_shelf_avail_status:failed',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.coriant.groove.shelfInletTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.coriant.groove.shelfOutletTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'coriant_groove_card_admin_status:up',
            'coriant_groove_card_alias_name:driving zombies forward oxen driving their',
            'coriant_groove_card_equipment_name:driving forward acted forward forward quaintly',
            'coriant_groove_card_mode:regen',
            'coriant_groove_card_oper_status:down',
            'coriant_groove_card_required_type:chm1lh',
            'coriant_groove_card_avail_status:lower_layer_down',
        ],
        [
            'coriant_groove_card_admin_status:up_no_alm',
            'coriant_groove_card_alias_name:Jaded kept quaintly forward Jaded',
            'coriant_groove_card_equipment_name:their',
            'coriant_groove_card_mode:not_applicable',
            'coriant_groove_card_oper_status:up',
            'coriant_groove_card_required_type:chm1',
            'coriant_groove_card_avail_status:mismatch',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.coriant.groove.cardFanSpeedRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.coriant.groove.cardTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'coriant_groove_port_alias_name:Jaded kept their',
            'coriant_groove_port_connected_to:forward zombies forward Jaded forward forward quaintly oxen',
            'coriant_groove_port_name:Jaded',
            'coriant_groove_port_service_label:zombies driving but zombies',
        ],
        [
            'coriant_groove_port_alias_name:oxen their',
            'coriant_groove_port_connected_to:driving kept but',
            'coriant_groove_port_name:driving kept oxen',
            'coriant_groove_port_service_label:driving acted acted quaintly',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.coriant.groove.portRxOpticalPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.coriant.groove.portTxOpticalPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['coriant_groove_och_os_service_label:oxen but quaintly forward but'],
        ['coriant_groove_och_os_service_label:their quaintly driving their kept their forward zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.coriant.groove.ochOsCD', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.coriant.groove.ochOsOSNR', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'infinera-coriant-groove Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'infinera-coriant-groove.device.name',
        'profile': 'infinera-coriant-groove',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.42229.1.2',
        'vendor': 'infinera',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
