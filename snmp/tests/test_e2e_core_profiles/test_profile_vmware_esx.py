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
    assert_extend_generic_host_resources_base,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_vmware_esx(dd_agent_check):
    profile = 'vmware-esx'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:vmware-esx',
        'snmp_host:vmware-esx.device.name',
        'device_hostname:vmware-esx.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['vmw_hba_device_name:but but', 'vmw_hba_status:failed'],
        ['vmw_hba_device_name:driving acted but their but', 'vmw_hba_status:failed'],
        ['vmw_hba_device_name:quaintly forward quaintly', 'vmw_hba_status:failed'],
        ['vmw_hba_device_name:zombies quaintly', 'vmw_hba_status:failed'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.vmwHostBusAdapter', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['vmw_hardware_status:normal', 'vmw_subsystem_type:raid_controller'],
        ['vmw_hardware_status:unknown', 'vmw_subsystem_type:raid_controller'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.vmwEnv', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'vmware-esx Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'vmware-esx.device.name',
        'profile': 'vmware-esx',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.6876.4.1',
        'vendor': 'vmware',
        'device_type': 'server',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
