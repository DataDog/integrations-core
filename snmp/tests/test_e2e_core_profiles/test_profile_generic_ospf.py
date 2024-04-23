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


def test_e2e_profile_generic_ospf(dd_agent_check):
    profile = '_generic-ospf'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:generic-ospf',
        'snmp_host:_generic-ospf.device.name',
        'device_hostname:_generic-ospf.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['neighbor_id:133.138.249.246', 'neighbor_ip:94.202.136.147', 'neighbor_state:down'],
        ['neighbor_id:197.51.68.111', 'neighbor_ip:14.178.122.218', 'neighbor_state:attempt'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ospfNbr', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ospfNbrEvents', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ospfNbrLsRetransQLen', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ospfNbrState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['neighbor_id:178.106.85.220', 'neighbor_ip:67.70.58.60', 'neighbor_state:exchange'],
        ['neighbor_id:32.2.154.12', 'neighbor_ip:18.41.36.26', 'neighbor_state:exchange'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ospfVirtNbr', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ospfVirtNbrEvents', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.ospfVirtNbrLsRetransQLen', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.ospfVirtNbrState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['if_state:backup_designated_router', 'neighbor_id:197.51.68.111', 'ospf_ip_addr:153.137.11.77'],
        ['if_state:point_to_point', 'neighbor_id:133.138.249.246', 'ospf_ip_addr:185.206.44.173'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ospfIfLsaCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ospfIfRetransInterval', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ospfIfState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['if_state:backup_designated_router', 'neighbor_id:197.51.68.111', 'ospf_ip_addr:153.137.11.77'],
        ['if_state:point_to_point', 'neighbor_id:133.138.249.246', 'ospf_ip_addr:185.206.44.173'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ospfIf', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['if_state:point_to_point', 'neighbor_id:178.106.85.220'],
        ['if_state:point_to_point', 'neighbor_id:32.2.154.12'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ospfVirtIfLsaCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.ospfVirtIfRetransInterval', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.ospfVirtIfState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['if_state:point_to_point', 'neighbor_id:178.106.85.220'],
        ['if_state:point_to_point', 'neighbor_id:32.2.154.12'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ospfVirtIf', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': '_generic-ospf Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_generic-ospf.device.name',
        'profile': 'generic-ospf',
        'status': 1,
        'sys_object_id': '1.2.3.3294.1281',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
