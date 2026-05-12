# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from unittest.mock import MagicMock

import pytest
from requests.exceptions import ConnectionError, HTTPError

from datadog_checks.dell_powerflex import DellPowerflexCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    DEVICE_ONLY_METRICS,
    DEVICE_STATS_BWC_METRICS,
    DEVICE_STATS_SIMPLE_METRICS,
    PROTECTION_DOMAIN_STATS_BWC_METRICS,
    PROTECTION_DOMAIN_STATS_SIMPLE_METRICS,
    RESOURCE_STATS_METRIC,
    SDC_STATS_BWC_METRICS,
    SDC_STATS_SIMPLE_METRICS,
    SDS_STATS_BWC_METRICS,
    SDS_STATS_SIMPLE_METRICS,
    STORAGE_POOL_STATS_BWC_METRICS,
    STORAGE_POOL_STATS_SIMPLE_METRICS,
    SYSTEM_MDM_CLUSTER_METRICS,
    SYSTEM_STATS_BWC_METRICS,
    SYSTEM_STATS_SIMPLE_METRICS,
    VOLUME_STATS_BWC_METRICS,
    VOLUME_STATS_SIMPLE_METRICS,
)

pytestmark = [pytest.mark.unit]


def assert_bwc_metrics(aggregator, bwc_metrics, tags, value=0):
    for metric_prefix in bwc_metrics:
        aggregator.assert_metric(f'{metric_prefix}.num_seconds', value=value, tags=tags)
        aggregator.assert_metric(f'{metric_prefix}.total_weight_in_kb', value=value, tags=tags)
        aggregator.assert_metric(f'{metric_prefix}.num_occured', value=value, tags=tags)


def test_can_connect_down(dd_run_check, aggregator, instance, mocker):
    mocker.patch('requests.Session.get', side_effect=ConnectionError('connection refused'))
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'dell_powerflex.api.can_connect',
        value=0,
        tags=['powerflex_gateway_url:https://localhost:443'],
    )


def test_auth_failure(dd_run_check, aggregator, instance, mocker, caplog):
    response = MagicMock(status_code=401, reason='Unauthorized')
    response.raise_for_status.side_effect = HTTPError(response=response)
    mocker.patch('requests.Session.post', return_value=response)

    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    caplog.set_level(logging.WARNING)
    dd_run_check(check)

    aggregator.assert_metric(
        'dell_powerflex.api.can_connect',
        value=0,
        tags=['powerflex_gateway_url:https://localhost:443'],
    )
    assert 'Could not connect to PowerFlex Gateway' in caplog.text


def test_can_connect_up(dd_run_check, aggregator, instance, mock_auth, mocker):
    mocker.patch('requests.Session.get', return_value=MagicMock(raise_for_status=MagicMock()))
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'dell_powerflex.api.can_connect',
        value=1,
        tags=['powerflex_gateway_url:https://localhost:443'],
    )


def test_unauthenticated_mode(dd_run_check, aggregator, monkeypatch, mock_http_call, mocker):
    instance = {'powerflex_gateway_url': 'https://localhost:443'}
    mocker.patch(
        'requests.Session.get',
        side_effect=lambda url, *args, **kwargs: MagicMock(
            json=MagicMock(return_value=mock_http_call(url)), status_code=200
        ),
    )
    mock_post = mocker.patch('requests.Session.post')
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    mock_post.assert_not_called()
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', at_least=1)


def test_token_refresh_uses_min_collection_interval(dd_run_check, instance, mock_http_get, mocker):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])

    dd_run_check(check)
    spy = mocker.spy(check._api, '_authenticate')

    # Token still valid — no re-auth
    dd_run_check(check)
    assert spy.call_count == 0

    # Simulate token nearing expiry
    mocker.patch('datadog_checks.dell_powerflex.api.time', return_value=check._api._token_expiry - 10)
    dd_run_check(check)
    assert spy.call_count == 1


def test_collect_system(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    system_tags = base_tags + ['system_id:1fcf40fc60c6520f', 'dell_type:system']

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1, tags=base_tags)
    aggregator.assert_metric('dell_powerflex.system.count', value=1, tags=system_tags)

    for metric in SYSTEM_MDM_CLUSTER_METRICS:
        aggregator.assert_metric(
            metric['name'],
            value=metric['value'],
            tags=system_tags + metric.get('extra_tags', []),
        )

    for metric in SYSTEM_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=system_tags)

    assert_bwc_metrics(aggregator, SYSTEM_STATS_BWC_METRICS, system_tags)


def test_assert_all_metrics(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'device', 'property': 'name', 'patterns': ['.*'], 'collect_statistics': True},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_symmetric_inclusion=True)


def test_device_statistics_disabled_by_default(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    for metric in DEVICE_ONLY_METRICS:
        aggregator.assert_metric(metric, count=0)


def test_collect_volumes(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    # volumee: ThinProvisioned, mapped to one SDC, no ancestor
    volume_tags = base_tags + [
        'volume_id:c58b06e700000000',
        'volume_name:volumee',
        'volume_type:ThinProvisioned',
        'storage_pool_id:25155ba600000000',
        'dell_type:volume',
    ]
    aggregator.assert_metric('dell_powerflex.volume.count', value=1, tags=volume_tags)
    for metric in VOLUME_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=volume_tags)
    assert_bwc_metrics(aggregator, VOLUME_STATS_BWC_METRICS, volume_tags)
    # volume-to-SDC mapping metric
    aggregator.assert_metric(
        'dell_powerflex.volume.sdc_mapping', value=1, tags=volume_tags + ['sdc_id:1b8659fd00000001']
    )

    # bigvolume: ThinProvisioned, mapped to one SDC, no children
    bigvolume_tags = base_tags + [
        'volume_id:c58b06e800000001',
        'volume_name:bigvolume',
        'volume_type:ThinProvisioned',
        'storage_pool_id:25155ba600000000',
        'dell_type:volume',
    ]
    aggregator.assert_metric('dell_powerflex.num_of_child_volumes', value=0, tags=bigvolume_tags)
    aggregator.assert_metric('dell_powerflex.num_of_mapped_sdcs', value=1, tags=bigvolume_tags)
    aggregator.assert_metric(
        'dell_powerflex.volume.sdc_mapping', value=1, tags=bigvolume_tags + ['sdc_id:1b8659fd00000001']
    )

    # volumee-snap-01: Snapshot, no SDC mapping, has ancestor, 1 child
    snap01_tags = base_tags + [
        'volume_id:c58b06e900000002',
        'volume_name:volumee-snap-01',
        'volume_type:Snapshot',
        'storage_pool_id:25155ba600000000',
        'dell_type:volume',
        'ancestor_volume_id:c58b06e700000000',
    ]
    aggregator.assert_metric('dell_powerflex.num_of_child_volumes', value=1, tags=snap01_tags)
    aggregator.assert_metric('dell_powerflex.num_of_mapped_sdcs', value=0, tags=snap01_tags)

    # volumee-snap-02: Snapshot, no SDC mapping, has ancestor, no children
    snap02_tags = base_tags + [
        'volume_id:c58b06ea00000003',
        'volume_name:volumee-snap-02',
        'volume_type:Snapshot',
        'storage_pool_id:25155ba600000000',
        'dell_type:volume',
        'ancestor_volume_id:c58b06e900000002',
    ]
    aggregator.assert_metric('dell_powerflex.num_of_child_volumes', value=0, tags=snap02_tags)
    aggregator.assert_metric('dell_powerflex.num_of_mapped_sdcs', value=0, tags=snap02_tags)


def test_collect_storage_pools(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    pool_tags = base_tags + [
        'storage_pool_id:25155ba600000000',
        'storage_pool_name:pool1',
        'protection_domain_id:68c139ee00000000',
        'dell_type:storage_pool',
    ]
    aggregator.assert_metric('dell_powerflex.storage_pool.count', value=1, tags=pool_tags)
    for metric in STORAGE_POOL_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=pool_tags)
    assert_bwc_metrics(aggregator, STORAGE_POOL_STATS_BWC_METRICS, pool_tags)

    # storagepool2: HDD, empty pool, no ActualNetCapacityInUseInKb
    pool2_tags = base_tags + [
        'storage_pool_id:2515d0d600000001',
        'storage_pool_name:storagepool2',
        'protection_domain_id:68c139ee00000000',
        'dell_type:storage_pool',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', value=0, tags=pool2_tags)
    aggregator.assert_metric('dell_powerflex.max_capacity.in_kb', value=0, tags=pool2_tags)
    aggregator.assert_metric('dell_powerflex.num_of_volumes', value=0, tags=pool2_tags)
    assert_bwc_metrics(aggregator, STORAGE_POOL_STATS_BWC_METRICS, pool2_tags)


def test_collect_protection_domains(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    pd_tags = base_tags + [
        'protection_domain_id:68c139ee00000000',
        'protection_domain_name:domain1',
        'system_id:1fcf40fc60c6520f',
        'dell_type:protection_domain',
    ]
    aggregator.assert_metric('dell_powerflex.protection_domain.count', value=1, tags=pd_tags)
    for metric in PROTECTION_DOMAIN_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=pd_tags)
    assert_bwc_metrics(aggregator, PROTECTION_DOMAIN_STATS_BWC_METRICS, pd_tags)


@pytest.mark.parametrize(
    'method, num_items, log_message',
    [
        ('_collect_system', 1, 'Failed to collect metrics for system'),
        ('_collect_volume', 4, 'Failed to collect metrics for volume'),
        ('_collect_storage_pool', 2, 'Failed to collect metrics for storage pool'),
        ('_collect_protection_domain', 1, 'Failed to collect metrics for protection domain'),
        ('_collect_sds', 3, 'Failed to collect metrics for SDS'),
        ('_collect_sdc', 3, 'Failed to collect metrics for SDC'),
        ('_collect_device', 3, 'Failed to collect metrics for device'),
    ],
)
def test_collect_failure_continues(
    dd_run_check, aggregator, instance, mock_http_get, mocker, caplog, method, num_items, log_message
):
    mocker.patch(
        f'datadog_checks.dell_powerflex.check.DellPowerflexCheck.{method}',
        side_effect=[Exception()] + [None] * (num_items - 1),
    )
    caplog.set_level(logging.WARNING)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    assert log_message in caplog.text


def test_collector_failure_does_not_stop_next_collectors(
    dd_run_check, aggregator, instance, mock_http_get, mocker, caplog
):
    mocker.patch(
        'datadog_checks.dell_powerflex.api.PowerFlexAPI.get_sds_list',
        side_effect=Exception('API error'),
    )
    caplog.set_level(logging.WARNING)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    assert 'Failed during _collect_sds_list collection' in caplog.text

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    pool_tags = base_tags + [
        'storage_pool_id:25155ba600000000',
        'storage_pool_name:pool1',
        'protection_domain_id:68c139ee00000000',
        'dell_type:storage_pool',
    ]
    aggregator.assert_metric('dell_powerflex.storage_pool.count', value=1, tags=pool_tags)


def test_collect_sds(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']

    # SDS3: d1c062b700000000, has fault_set_id
    sds3_tags = base_tags + [
        'sds_id:d1c062b700000000',
        'sds_name:SDS3',
        'protection_domain_id:68c139ee00000000',
        'fault_set_id:faultset00000001',
        'dell_type:sds',
    ]
    aggregator.assert_metric('dell_powerflex.sds.count', value=1, tags=sds3_tags)
    for metric in SDS_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=sds3_tags)
    assert_bwc_metrics(aggregator, SDS_STATS_BWC_METRICS, sds3_tags)

    # SDS2: d1c062b800000001
    sds2_tags = base_tags + [
        'sds_id:d1c062b800000001',
        'sds_name:SDS2',
        'protection_domain_id:68c139ee00000000',
        'dell_type:sds',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', value=350208, tags=sds2_tags)
    aggregator.assert_metric('dell_powerflex.unused_capacity.in_kb', value=103406592, tags=sds2_tags)
    aggregator.assert_metric('dell_powerflex.num_of_devices', value=1, tags=sds2_tags)
    assert_bwc_metrics(aggregator, SDS_STATS_BWC_METRICS, sds2_tags)

    # SDS1: d1c062b900000002
    sds1_tags = base_tags + [
        'sds_id:d1c062b900000002',
        'sds_name:SDS1',
        'protection_domain_id:68c139ee00000000',
        'dell_type:sds',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', value=349184, tags=sds1_tags)
    aggregator.assert_metric('dell_powerflex.unused_capacity.in_kb', value=103407616, tags=sds1_tags)
    aggregator.assert_metric('dell_powerflex.num_of_devices', value=1, tags=sds1_tags)
    assert_bwc_metrics(aggregator, SDS_STATS_BWC_METRICS, sds1_tags)


def test_collect_sdc(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']

    # SDC1: 1b8659fd00000001, numOfMappedVolumes=2
    sdc1_tags = base_tags + [
        'sdc_id:1b8659fd00000001',
        'sdc_guid:33FC0AF2-5180-45D8-9BDC-8E2F78CD60BF',
        'sdc_type:AppSdc',
        'sdc_ip:10.0.1.250',
        'peer_mdm_id:mdm00000001',
        'dell_type:sdc',
    ]
    aggregator.assert_metric('dell_powerflex.sdc.count', value=1, tags=sdc1_tags)
    for metric in SDC_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=sdc1_tags)
    assert_bwc_metrics(aggregator, SDC_STATS_BWC_METRICS, sdc1_tags)

    # SDC2: 1b8659fc00000000, numOfMappedVolumes=0
    sdc2_tags = base_tags + [
        'sdc_id:1b8659fc00000000',
        'sdc_guid:BE3BC972-269A-4931-96B8-286BFA45C004',
        'sdc_type:AppSdc',
        'sdc_ip:10.0.1.223',
        'dell_type:sdc',
    ]
    aggregator.assert_metric('dell_powerflex.num_of_mapped_volumes', value=0, tags=sdc2_tags)
    assert_bwc_metrics(aggregator, SDC_STATS_BWC_METRICS, sdc2_tags)

    # SDC3: 1b8659fe00000002, numOfMappedVolumes=0
    sdc3_tags = base_tags + [
        'sdc_id:1b8659fe00000002',
        'sdc_guid:46EE0B53-B823-4E68-B0B4-41A2DEC5A425',
        'sdc_type:AppSdc',
        'sdc_ip:10.0.1.228',
        'dell_type:sdc',
    ]
    aggregator.assert_metric('dell_powerflex.num_of_mapped_volumes', value=0, tags=sdc3_tags)
    assert_bwc_metrics(aggregator, SDC_STATS_BWC_METRICS, sdc3_tags)


def test_collect_devices(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'device', 'property': 'name', 'patterns': ['.*'], 'collect_statistics': True},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']

    # Device1: f7fd7d0b00020000, sds1-dev1 - full assertions
    dev1_tags = base_tags + [
        'device_id:f7fd7d0b00020000',
        'device_name:sds1-dev1',
        'current_path_name:/dev/sdb',
        'storage_pool_id:25155ba600000000',
        'sds_id:d1c062b900000002',
        'dell_type:device',
    ]
    aggregator.assert_metric('dell_powerflex.device.count', value=1, tags=dev1_tags)
    for metric in DEVICE_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=dev1_tags)
    assert_bwc_metrics(aggregator, DEVICE_STATS_BWC_METRICS, dev1_tags)

    # Device2: f7fd7d0a00010000, sds2-dev1
    dev2_tags = base_tags + [
        'device_id:f7fd7d0a00010000',
        'device_name:sds2-dev1',
        'current_path_name:/dev/sdb',
        'storage_pool_id:25155ba600000000',
        'sds_id:d1c062b800000001',
        'dell_type:device',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', value=350208, tags=dev2_tags)
    aggregator.assert_metric('dell_powerflex.avg_read_latency_in_microsec', value=12793, tags=dev2_tags)
    assert_bwc_metrics(aggregator, DEVICE_STATS_BWC_METRICS, dev2_tags)

    # Device3: f7f77d0900000000, sds3-dev1
    dev3_tags = base_tags + [
        'device_id:f7f77d0900000000',
        'device_name:sds3-dev1',
        'current_path_name:/dev/sdb',
        'storage_pool_id:25155ba600000000',
        'sds_id:d1c062b700000000',
        'dell_type:device',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', value=349184, tags=dev3_tags)
    aggregator.assert_metric('dell_powerflex.avg_read_latency_in_microsec', value=10023, tags=dev3_tags)
    assert_bwc_metrics(aggregator, DEVICE_STATS_BWC_METRICS, dev3_tags)


def test_collect_system_with_name(dd_run_check, aggregator, instance, mock_auth, mocker):
    instances_response = [
        {
            'id': '1fcf40fc60c6520f',
            'name': 'my-powerflex',
            'mdmCluster': {
                'goodNodesNum': 3,
                'goodReplicasNum': 2,
                'clusterState': 'ClusteredNormal',
                'clusterMode': 'ThreeNodes',
            },
        }
    ]

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=instances_response if 'types/System/instances' in url else {})
        return resp

    mocker.patch('requests.Session.get', side_effect=mock_get)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    system_tags = [
        'powerflex_gateway_url:https://localhost:443',
        'system_id:1fcf40fc60c6520f',
        'dell_type:system',
        'system_name:my-powerflex',
    ]
    aggregator.assert_metric('dell_powerflex.mdm_cluster.good_nodes', value=3, tags=system_tags)
    aggregator.assert_metric('dell_powerflex.mdm_cluster.good_replicas', value=2, tags=system_tags)


def test_include_filter_by_name(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'storage_pool', 'property': 'name', 'patterns': ['^pool1$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    pool1_tags = base_tags + [
        'storage_pool_id:25155ba600000000',
        'storage_pool_name:pool1',
        'protection_domain_id:68c139ee00000000',
        'dell_type:storage_pool',
    ]
    pool2_tags = base_tags + [
        'storage_pool_id:2515d0d600000001',
        'storage_pool_name:storagepool2',
        'protection_domain_id:68c139ee00000000',
        'dell_type:storage_pool',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=1, tags=pool1_tags)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=pool2_tags)


def test_exclude_filter_by_name(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'type': 'exclude', 'patterns': ['^SDS3$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    sds3_tags = base_tags + [
        'sds_id:d1c062b700000000',
        'sds_name:SDS3',
        'protection_domain_id:68c139ee00000000',
        'fault_set_id:faultset00000001',
        'dell_type:sds',
    ]
    sds2_tags = base_tags + [
        'sds_id:d1c062b800000001',
        'sds_name:SDS2',
        'protection_domain_id:68c139ee00000000',
        'dell_type:sds',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=sds3_tags)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=1, tags=sds2_tags)


def test_exclude_takes_precedence_over_include(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'storage_pool', 'property': 'name', 'patterns': ['.*']},
        {'resource': 'storage_pool', 'property': 'name', 'type': 'exclude', 'patterns': ['^pool1$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    pool1_tags = base_tags + [
        'storage_pool_id:25155ba600000000',
        'storage_pool_name:pool1',
        'protection_domain_id:68c139ee00000000',
        'dell_type:storage_pool',
    ]
    pool2_tags = base_tags + [
        'storage_pool_id:2515d0d600000001',
        'storage_pool_name:storagepool2',
        'protection_domain_id:68c139ee00000000',
        'dell_type:storage_pool',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=pool1_tags)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', tags=pool2_tags)


def test_collect_statistics_false(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'patterns': ['.*'], 'collect_statistics': False},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    sds3_tags = base_tags + [
        'sds_id:d1c062b700000000',
        'sds_name:SDS3',
        'protection_domain_id:68c139ee00000000',
        'fault_set_id:faultset00000001',
        'dell_type:sds',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=sds3_tags)
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)


def test_collect_statistics_false_without_patterns(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'collect_statistics': False},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    sds3_tags = base_tags + [
        'sds_id:d1c062b700000000',
        'sds_name:SDS3',
        'protection_domain_id:68c139ee00000000',
        'fault_set_id:faultset00000001',
        'dell_type:sds',
    ]
    # SDS resources are still collected
    aggregator.assert_metric('dell_powerflex.sds.count', value=1, tags=sds3_tags)
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    # But statistics are not collected
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=sds3_tags)


def test_filter_by_volume_type(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'volume', 'property': 'volumeType', 'patterns': ['^ThinProvisioned$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    volumee_tags = base_tags + [
        'volume_id:c58b06e700000000',
        'volume_name:volumee',
        'volume_type:ThinProvisioned',
        'storage_pool_id:25155ba600000000',
        'dell_type:volume',
    ]
    snap_tags = base_tags + [
        'volume_id:c58b06e900000002',
        'volume_name:volumee-snap-01',
        'volume_type:Snapshot',
        'storage_pool_id:25155ba600000000',
        'ancestor_volume_id:c58b06e700000000',
        'dell_type:volume',
    ]
    aggregator.assert_metric('dell_powerflex.num_of_child_volumes', tags=volumee_tags)
    aggregator.assert_metric('dell_powerflex.num_of_child_volumes', count=0, tags=snap_tags)


def test_unfiltered_resources_not_affected(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'patterns': ['^nonexistent$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    sds3_tags = base_tags + [
        'sds_id:d1c062b700000000',
        'sds_name:SDS3',
        'protection_domain_id:68c139ee00000000',
        'fault_set_id:faultset00000001',
        'dell_type:sds',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=sds3_tags)
    pool_tags = base_tags + [
        'storage_pool_id:25155ba600000000',
        'storage_pool_name:pool1',
        'protection_domain_id:68c139ee00000000',
        'dell_type:storage_pool',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', tags=pool_tags)


def test_multiple_filters_same_resource_type(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'patterns': ['^SDS[12]$']},
        {'resource': 'sds', 'property': 'id', 'type': 'exclude', 'patterns': ['^d1c062b800000001$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    sds1_tags = base_tags + [
        'sds_id:d1c062b900000002',
        'sds_name:SDS1',
        'protection_domain_id:68c139ee00000000',
        'dell_type:sds',
    ]
    sds2_tags = base_tags + [
        'sds_id:d1c062b800000001',
        'sds_name:SDS2',
        'protection_domain_id:68c139ee00000000',
        'dell_type:sds',
    ]
    sds3_tags = base_tags + [
        'sds_id:d1c062b700000000',
        'sds_name:SDS3',
        'protection_domain_id:68c139ee00000000',
        'fault_set_id:faultset00000001',
        'dell_type:sds',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=1, tags=sds1_tags)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=sds2_tags)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=sds3_tags)


@pytest.mark.parametrize(
    'resource_filters, log_message',
    [
        pytest.param(
            [{'resource': 'invalid_type', 'property': 'name', 'patterns': ['.*']}],
            'Invalid resource type',
            id='invalid_resource_type',
        ),
        pytest.param(
            [{'resource': 'sds', 'property': '', 'patterns': ['.*']}],
            'Missing or invalid property',
            id='missing_property_in_filter',
        ),
        pytest.param(
            [{'resource': 'sds', 'property': 'name'}],
            'No valid patterns',
            id='no_valid_patterns',
        ),
        pytest.param(
            [{'resource': 'sds', 'property': 'name', 'patterns': ['[invalid']}],
            'Invalid regex pattern',
            id='invalid_regex',
        ),
        pytest.param(
            [{'resource': 'sds', 'property': 'name', 'type': 'bad', 'patterns': ['.*']}],
            'Invalid filter type',
            id='invalid_filter_type',
        ),
    ],
)
def test_filter_validation_warning(
    dd_run_check, aggregator, instance, mock_http_get, caplog, resource_filters, log_message
):
    instance['resource_filters'] = resource_filters
    caplog.set_level(logging.WARNING)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    assert log_message in caplog.text
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)


@pytest.mark.parametrize(
    'resource_filters, log_message',
    [
        pytest.param(
            [{'resource': 'sds', 'property': 'name', 'type': 'exclude', 'patterns': ['^SDS3$']}],
            'Skipping sds SDS3: matched exclude pattern',
            id='exclude_filter',
        ),
        pytest.param(
            [{'resource': 'storage_pool', 'property': 'name', 'patterns': ['^pool1$']}],
            'Skipping storage_pool storagepool2: did not match any include pattern',
            id='include_filter',
        ),
        pytest.param(
            [{'resource': 'sds', 'property': 'nonexistent_field', 'patterns': ['.*']}],
            'property nonexistent_field not found',
            id='missing_property',
        ),
    ],
)
def test_filter_logs_debug(dd_run_check, aggregator, instance, mock_http_get, caplog, resource_filters, log_message):
    instance['resource_filters'] = resource_filters
    caplog.set_level(logging.DEBUG)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    assert log_message in caplog.text


def test_exclude_filter_missing_property(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'nonexistent_field', 'type': 'exclude', 'patterns': ['.*']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    base_tags = ['powerflex_gateway_url:https://localhost:443']
    sds_tags = base_tags + [
        'sds_id:d1c062b700000000',
        'sds_name:SDS3',
        'protection_domain_id:68c139ee00000000',
        'fault_set_id:faultset00000001',
        'dell_type:sds',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', tags=sds_tags)


def test_non_string_pattern_skipped(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'patterns': [123, '.*']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    base_tags = ['powerflex_gateway_url:https://localhost:443']
    sds3_tags = base_tags + [
        'sds_id:d1c062b700000000',
        'sds_name:SDS3',
        'protection_domain_id:68c139ee00000000',
        'fault_set_id:faultset00000001',
        'dell_type:sds',
    ]
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', tags=sds3_tags)


@pytest.mark.parametrize(
    'resource, property, patterns',
    [
        ('protection_domain', 'name', ['^nonexistent$']),
        ('sdc', 'sdcIp', ['^192\\.168\\.']),
        ('device', 'name', ['^nonexistent$']),
    ],
)
def test_filter_excludes_all_resources(dd_run_check, aggregator, instance, mock_http_get, resource, property, patterns):
    instance['resource_filters'] = [
        {'resource': resource, 'property': property, 'patterns': patterns},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    metric_name, tag_subset = RESOURCE_STATS_METRIC[resource]
    matching = [m for m in aggregator.metrics(metric_name) if all(t in m.tags for t in tag_subset)]
    assert len(matching) == 0, f'Expected no {metric_name} with {tag_subset}, got {len(matching)}'


@pytest.mark.parametrize(
    'resource, property',
    [
        ('volume', 'name'),
        ('storage_pool', 'name'),
        ('protection_domain', 'name'),
        ('sds', 'name'),
        ('sdc', 'sdcType'),
        ('device', 'name'),
    ],
)
def test_collect_statistics_false_per_resource(dd_run_check, aggregator, instance, mock_http_get, resource, property):
    instance['resource_filters'] = [
        {'resource': resource, 'property': property, 'patterns': ['.*'], 'collect_statistics': False},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    metric_name, tag_subset = RESOURCE_STATS_METRIC[resource]
    matching = [m for m in aggregator.metrics(metric_name) if all(t in m.tags for t in tag_subset)]
    assert len(matching) == 0, f'Expected no {metric_name} with {tag_subset}, got {len(matching)}'


def test_collect_events(dd_run_check, aggregator, instance, mock_http_get):
    instance['collect_events'] = True
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    events = aggregator.events
    assert len(events) == 5
    for event in events:
        assert event['alert_type'] == 'error'
        assert event['event_type'] == 'dell_powerflex'
        assert event['source_type_name'] == 'dell_powerflex'
        assert 'severity:CRITICAL' in event['tags']
        assert 'powerflex_gateway_url:https://localhost:443' in event['tags']

    titles = [e['msg_title'] for e in events]
    assert 'Health Check Failed' in titles
    assert 'Unknown Snmp Trap' in titles

    health_check_event = next(e for e in events if e['msg_title'] == 'Health Check Failed')
    assert (
        'pfm-asmmanager: Health check failed: SDNAS Gateway pod failed to response.' in health_check_event['msg_text']
    )
    assert 'powerflex_event_name:HEALTH_CHECK_FAILED' in health_check_event['tags']
    assert 'category:AUDIT' in health_check_event['tags']
    assert 'domain:MANAGEMENT' in health_check_event['tags']
    assert 'service_name:pfm-asmmanager' in health_check_event['tags']


def test_collect_events_first_run_uses_current_time(dd_run_check, aggregator, instance, mock_http_get, mocker):
    instance['collect_events'] = True
    mock_get_events = mocker.patch(
        'datadog_checks.dell_powerflex.api.PowerFlexAPI.get_events',
        return_value=[],
    )
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    since_arg = mock_get_events.call_args[1].get('since') or mock_get_events.call_args[0][0]
    assert since_arg is not None
    assert since_arg.endswith('Z')
    assert len(aggregator.events) == 0


def test_collect_events_subsequent_run_uses_cached_time(dd_run_check, aggregator, instance, mock_http_get, mocker):
    instance['collect_events'] = True
    mock_get_events = mocker.patch(
        'datadog_checks.dell_powerflex.api.PowerFlexAPI.get_events',
        return_value=[],
    )
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    # First run seeds the cache
    dd_run_check(check)
    # Overwrite cache with a known timestamp
    check.write_persistent_cache('last_event_timestamp', '2026-01-01T00:00:00Z')
    # Second run should use the cached timestamp
    dd_run_check(check)

    since_arg = mock_get_events.call_args[1].get('since') or mock_get_events.call_args[0][0]
    assert since_arg == '2026-01-01T00:00:00Z'


@pytest.mark.parametrize('config_key', ['collect_events', 'collect_alerts'])
def test_collect_disabled(dd_run_check, aggregator, instance, mock_http_get, config_key):
    instance[config_key] = False
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)


@pytest.mark.parametrize(
    'config_key, mock_target, log_message',
    [
        ('collect_events', 'datadog_checks.dell_powerflex.api.PowerFlexAPI.get_events', 'Failed to collect events'),
        ('collect_alerts', 'datadog_checks.dell_powerflex.api.PowerFlexAPI.get_alerts', 'Failed to collect alerts'),
    ],
)
def test_collect_failure(
    dd_run_check, aggregator, instance, mock_http_get, mocker, caplog, config_key, mock_target, log_message
):
    instance[config_key] = True
    mocker.patch(mock_target, side_effect=Exception(f'{config_key} API failed'))
    caplog.set_level(logging.WARNING)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    assert log_message in caplog.text
    assert len(aggregator.events) == 0
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)


def test_collect_alerts(dd_run_check, aggregator, instance, mock_http_get):
    instance['collect_alerts'] = True
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    alerts = aggregator.events
    assert len(alerts) == 2
    for alert in alerts:
        assert alert['event_type'] == 'dell_powerflex'
        assert alert['source_type_name'] == 'dell_powerflex'
        assert 'powerflex_gateway_url:https://localhost:443' in alert['tags']

    mdm_alert = next(a for a in alerts if a['msg_title'] == 'Unable To Receive Mdm Events')
    assert mdm_alert['alert_type'] == 'error'
    assert 'MDM1: Unable to receive mdm events from [10.0.1.250] .' in mdm_alert['msg_text']
    assert 'powerflex_alert_name:UNABLE_TO_RECEIVE_MDM_EVENTS' in mdm_alert['tags']
    assert 'severity:MAJOR' in mdm_alert['tags']
    assert 'category:MAINTENANCE' in mdm_alert['tags']
    assert 'domain:BLOCK' in mdm_alert['tags']
    assert 'dell_type:mdms' in mdm_alert['tags']
    assert 'service_name:block-events-gw' in mdm_alert['tags']

    license_alert = next(a for a in alerts if a['msg_title'] == 'Trial License Used')
    assert license_alert['alert_type'] == 'warning'
    assert 'PowerFlex is using a trial license' in license_alert['msg_text']
    assert 'severity:MINOR' in license_alert['tags']
