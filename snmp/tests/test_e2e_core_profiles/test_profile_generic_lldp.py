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
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_generic_lldp(dd_agent_check):
    profile = '_generic-lldp'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:generic-lldp',
        'snmp_host:_generic-lldp-mib.device.name',
        'device_hostname:_generic-lldp-mib.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    metric_tags = common_tags + [
        'lldp_rem_port_id:driving quaintly oxen but their oxen driving',
        'lldp_rem_port_id_subtype:interface_alias',
        'lldp_rem_sys_name:forward Jaded their Jaded zombies driving quaintly acted',
    ]
    aggregator.assert_metric('snmp.lldpRem', metric_type=aggregator.GAUGE, tags=metric_tags)

    # --- TEST METADATA ---
    device = {
        'description': '_generic-lldp-mib Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_generic-lldp-mib.device.name',
        'profile': 'generic-lldp',
        'status': 1,
        'sys_object_id': '1.2.3.99999',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
