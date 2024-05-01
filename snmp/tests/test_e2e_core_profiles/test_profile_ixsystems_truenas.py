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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_ixsystems_truenas(dd_agent_check):
    profile = 'ixsystems-truenas'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:ixsystems-truenas',
        'snmp_host:ixsystems-truenas.device.name',
        'device_hostname:ixsystems-truenas.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.freenas.zfsArcC', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsArcCacheHitRatio', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsArcCacheMissRatio', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsArcData', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsArcHits', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsArcMeta', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsArcMissPercent', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsArcMisses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsArcP', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsArcSize', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsL2ArcHits', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsL2ArcMisses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsL2ArcRead', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsL2ArcSize', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsL2ArcWrite', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsZilstatOps10sec', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsZilstatOps1sec', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.freenas.zfsZilstatOps5sec', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['freenas_zpool_descr:Jaded Jaded'],
        ['freenas_zpool_descr:quaintly Jaded oxen kept forward their their quaintly but'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.freenas.zpoolAllocationUnits', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.freenas.zpoolAvailable', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.freenas.zpoolHealth', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.freenas.zpoolReadBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.freenas.zpoolReadBytes1sec', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.freenas.zpoolReadOps', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.freenas.zpoolReadOps1sec', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.freenas.zpoolSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.freenas.zpoolUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.freenas.zpoolWriteBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.freenas.zpoolWriteBytes1sec', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.freenas.zpoolWriteOps', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.freenas.zpoolWriteOps1sec', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['freenas_dataset_descr:quaintly driving quaintly zombies'],
        ['freenas_dataset_descr:their forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.freenas.datasetAllocationUnits', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.freenas.datasetAvailable', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.freenas.datasetSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.freenas.datasetUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['freenas_zvol_descr:zombies Jaded kept'],
        ['freenas_zvol_descr:zombies quaintly forward Jaded'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.freenas.zvolAllocationUnits', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.freenas.zvolAvailable', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.freenas.zvolReferenced', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.freenas.zvolSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.freenas.zvolUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'ixsystems-truenas Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'ixsystems-truenas.device.name',
        'profile': 'ixsystems-truenas',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.50536.3.2',
        'vendor': 'iXsystems',
        'device_type': 'storage',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
