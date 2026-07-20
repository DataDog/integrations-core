# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPConnectionError, HTTPStatusError
from datadog_checks.dell_powerflex import DellPowerflexCheck
from datadog_checks.dev.http import MockHTTPResponse
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    ALL_EXPECTED_METRICS,
    BASE_TAGS,
    DEFAULT_GATEWAY_URL,
    DEV1_TAGS,
    DEV2_TAGS,
    DEV3_TAGS,
    DEVICE_ONLY_METRICS,
    DEVICE_STATS_BWC_METRICS,
    DEVICE_STATS_SIMPLE_METRICS,
    PD_TAGS,
    POOL1_TAGS,
    POOL2_TAGS,
    PROTECTION_DOMAIN_STATS_BWC_METRICS,
    PROTECTION_DOMAIN_STATS_SIMPLE_METRICS,
    SDC1_TAGS,
    SDC2_TAGS,
    SDC3_TAGS,
    SDC_STATS_BWC_METRICS,
    SDC_STATS_SIMPLE_METRICS,
    SDS1_TAGS,
    SDS2_TAGS,
    SDS3_TAGS,
    SDS_STATS_BWC_METRICS,
    SDS_STATS_SIMPLE_METRICS,
    STORAGE_POOL_STATS_BWC_METRICS,
    STORAGE_POOL_STATS_SIMPLE_METRICS,
    SYSTEM_MDM_CLUSTER_METRICS,
    SYSTEM_STATS_BWC_METRICS,
    SYSTEM_STATS_SIMPLE_METRICS,
    SYSTEM_TAGS,
    VOL_BIGVOLUME_TAGS,
    VOL_SNAP1_TAGS,
    VOL_SNAP2_TAGS,
    VOL_VOLUMEE_TAGS,
    VOLUME_STATS_BWC_METRICS,
    VOLUME_STATS_SIMPLE_METRICS,
)

pytestmark = [pytest.mark.unit]


def assert_bwc_metrics(aggregator, bwc_metrics, tags, value=0):
    for metric_prefix in bwc_metrics:
        aggregator.assert_metric(f'{metric_prefix}.num_seconds', value=value, tags=tags)
        aggregator.assert_metric(f'{metric_prefix}.total_weight_in_kb', value=value, tags=tags)
        aggregator.assert_metric(f'{metric_prefix}.num_occured', value=value, tags=tags)


def test_can_connect_down(dd_run_check, aggregator, instance, mock_http):
    mock_http.post.side_effect = HTTPConnectionError('connection refused')
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=0, tags=BASE_TAGS)


def test_auth_response_missing_access_token(dd_run_check, aggregator, instance, mock_http, caplog):
    mock_http.post.side_effect = lambda *a, **k: MockHTTPResponse(
        json_data={'error': 'unauthorized_client'}, status_code=200
    )
    caplog.set_level(logging.WARNING)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=0, tags=BASE_TAGS)
    assert 'Auth response missing access_token' in caplog.text


def test_version_failure(dd_run_check, aggregator, instance, mock_auth, mock_http, caplog):
    mock_http.get.side_effect = HTTPStatusError('500 Server Error', response=MockHTTPResponse(status_code=500))

    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    caplog.set_level(logging.WARNING)
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=0, tags=BASE_TAGS)
    assert 'Could not connect to PowerFlex Gateway' in caplog.text


def test_can_connect_up(dd_run_check, aggregator, instance, mock_auth, mock_http):
    mock_http.get.side_effect = lambda *a, **k: MockHTTPResponse(json_data={}, status_code=200)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1, tags=BASE_TAGS)


def test_unauthenticated_mode(dd_run_check, aggregator, mock_http_call, mock_http):
    instance = {'powerflex_gateway_url': DEFAULT_GATEWAY_URL}
    mock_http.get.side_effect = lambda url, *args, **kwargs: MockHTTPResponse(
        json_data=mock_http_call(url), status_code=200
    )
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    mock_http.post.assert_not_called()
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', at_least=1)
    aggregator.assert_metric('dell_powerflex.system.count', at_least=1)
    aggregator.assert_metric('dell_powerflex.storage_pool.count', at_least=1)
    aggregator.assert_metric('dell_powerflex.volume.count', at_least=1)


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

    system_tags = BASE_TAGS + SYSTEM_TAGS

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1, tags=BASE_TAGS)
    aggregator.assert_metric('dell_powerflex.system.count', value=1, tags=system_tags)

    for metric in SYSTEM_MDM_CLUSTER_METRICS:
        aggregator.assert_metric(
            metric['name'],
            value=metric['value'],
            tags=system_tags + metric.get('extra_tags', []),
        )

    for metric in SYSTEM_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=system_tags)

    assert_bwc_metrics(
        aggregator, [m for m in SYSTEM_STATS_BWC_METRICS if m != 'dell_powerflex.user_data_read_bwc'], system_tags
    )
    # userDataReadBwc fixture has numOccured=42
    aggregator.assert_metric('dell_powerflex.user_data_read_bwc.num_seconds', value=0, tags=system_tags)
    aggregator.assert_metric('dell_powerflex.user_data_read_bwc.total_weight_in_kb', value=0, tags=system_tags)
    aggregator.assert_metric('dell_powerflex.user_data_read_bwc.num_occured', value=42, tags=system_tags)


def test_assert_all_metrics(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'device', 'property': 'name', 'patterns': ['.*'], 'collect_statistics': True},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    for metric in ALL_EXPECTED_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=BASE_TAGS + metric['tags'])

    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), check_symmetric_inclusion=True, check_submission_type=True
    )


def test_device_statistics_disabled_by_default(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    for metric in DEVICE_ONLY_METRICS:
        aggregator.assert_metric(metric, count=0)


def test_collect_volumes(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    # volumee: ThinProvisioned, mapped to one SDC, no ancestor
    volume_tags = BASE_TAGS + VOL_VOLUMEE_TAGS
    aggregator.assert_metric('dell_powerflex.volume.count', value=1, tags=volume_tags)
    for metric in VOLUME_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=volume_tags)
    assert_bwc_metrics(aggregator, VOLUME_STATS_BWC_METRICS, volume_tags)
    aggregator.assert_metric(
        'dell_powerflex.volume.sdc_mapping', value=1, tags=volume_tags + ['sdc_id:1b8659fd00000001']
    )

    # bigvolume: ThinProvisioned, mapped to one SDC, no children
    bigvolume_tags = BASE_TAGS + VOL_BIGVOLUME_TAGS
    aggregator.assert_metric('dell_powerflex.volume.count', value=1, tags=bigvolume_tags)
    aggregator.assert_metric('dell_powerflex.num_of_child_volumes', value=0, tags=bigvolume_tags)
    aggregator.assert_metric('dell_powerflex.num_of_mapped_sdcs', value=1, tags=bigvolume_tags)
    aggregator.assert_metric(
        'dell_powerflex.volume.sdc_mapping', value=1, tags=bigvolume_tags + ['sdc_id:1b8659fd00000001']
    )

    for snap_resource_tags, children in [(VOL_SNAP1_TAGS, 1), (VOL_SNAP2_TAGS, 0)]:
        snap_tags = BASE_TAGS + snap_resource_tags
        aggregator.assert_metric('dell_powerflex.volume.count', value=1, tags=snap_tags)
        aggregator.assert_metric('dell_powerflex.num_of_child_volumes', value=children, tags=snap_tags)
        aggregator.assert_metric('dell_powerflex.num_of_mapped_sdcs', value=0, tags=snap_tags)


def test_collect_storage_pools(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    pool_tags = BASE_TAGS + POOL1_TAGS
    aggregator.assert_metric('dell_powerflex.storage_pool.count', value=1, tags=pool_tags)
    for metric in STORAGE_POOL_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=pool_tags)
    assert_bwc_metrics(aggregator, STORAGE_POOL_STATS_BWC_METRICS, pool_tags)

    # storagepool2: HDD, empty pool, no ActualNetCapacityInUseInKb
    pool2_tags = BASE_TAGS + POOL2_TAGS
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', value=0, tags=pool2_tags)
    aggregator.assert_metric('dell_powerflex.max_capacity.in_kb', value=0, tags=pool2_tags)
    aggregator.assert_metric('dell_powerflex.num_of_volumes', value=0, tags=pool2_tags)
    assert_bwc_metrics(aggregator, STORAGE_POOL_STATS_BWC_METRICS, pool2_tags)


def test_collect_protection_domains(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    pd_tags = BASE_TAGS + PD_TAGS
    aggregator.assert_metric('dell_powerflex.protection_domain.count', value=1, tags=pd_tags)
    for metric in PROTECTION_DOMAIN_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=pd_tags)
    assert_bwc_metrics(aggregator, PROTECTION_DOMAIN_STATS_BWC_METRICS, pd_tags)


@pytest.mark.parametrize(
    'method, log_message',
    [
        ('_collect_system', 'Failed to collect metrics for system'),
        ('_collect_volume', 'Failed to collect metrics for volume'),
        ('_collect_storage_pool', 'Failed to collect metrics for storage pool'),
        ('_collect_protection_domain', 'Failed to collect metrics for protection domain'),
        ('_collect_sds', 'Failed to collect metrics for SDS'),
        ('_collect_sdc', 'Failed to collect metrics for SDC'),
        ('_collect_device', 'Failed to collect metrics for device'),
    ],
)
def test_resource_collect_failure(
    dd_run_check, aggregator, instance, mock_http_get, mocker, caplog, method, log_message
):
    mocker.patch(
        f'datadog_checks.dell_powerflex.check.DellPowerflexCheck.{method}',
        side_effect=Exception(),
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
    aggregator.assert_metric('dell_powerflex.storage_pool.count', value=1, tags=BASE_TAGS + POOL1_TAGS)


def test_collect_sds(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    # SDS3: d1c062b700000000, has fault_set_id
    sds3_tags = BASE_TAGS + SDS3_TAGS
    aggregator.assert_metric('dell_powerflex.sds.count', value=1, tags=sds3_tags)
    for metric in SDS_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=sds3_tags)
    assert_bwc_metrics(aggregator, SDS_STATS_BWC_METRICS, sds3_tags)

    for sds_resource_tags, cap, unused in [
        (SDS2_TAGS, 350208, 103406592),
        (SDS1_TAGS, 349184, 103407616),
    ]:
        tags = BASE_TAGS + sds_resource_tags
        aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', value=cap, tags=tags)
        aggregator.assert_metric('dell_powerflex.unused_capacity.in_kb', value=unused, tags=tags)
        aggregator.assert_metric('dell_powerflex.num_of_devices', value=1, tags=tags)
        assert_bwc_metrics(aggregator, SDS_STATS_BWC_METRICS, tags)


def test_collect_sdc(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    # SDC1: 1b8659fd00000001, numOfMappedVolumes=2
    sdc1_tags = BASE_TAGS + SDC1_TAGS
    aggregator.assert_metric('dell_powerflex.sdc.count', value=1, tags=sdc1_tags)
    for metric in SDC_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=sdc1_tags)
    assert_bwc_metrics(aggregator, SDC_STATS_BWC_METRICS, sdc1_tags)

    for sdc_resource_tags in [SDC2_TAGS, SDC3_TAGS]:
        tags = BASE_TAGS + sdc_resource_tags
        aggregator.assert_metric('dell_powerflex.num_of_mapped_volumes', value=0, tags=tags)
        assert_bwc_metrics(aggregator, SDC_STATS_BWC_METRICS, tags)


def test_collect_devices(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'device', 'property': 'name', 'patterns': ['.*'], 'collect_statistics': True},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    # Device1: f7fd7d0b00020000, sds1-dev1 - full assertions
    dev1_tags = BASE_TAGS + DEV1_TAGS
    aggregator.assert_metric('dell_powerflex.device.count', value=1, tags=dev1_tags)
    for metric in DEVICE_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=dev1_tags)
    assert_bwc_metrics(aggregator, DEVICE_STATS_BWC_METRICS, dev1_tags)

    for dev_resource_tags, cap, latency in [
        (DEV2_TAGS, 350208, 12793),
        (DEV3_TAGS, 349184, 10023),
    ]:
        tags = BASE_TAGS + dev_resource_tags
        aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', value=cap, tags=tags)
        aggregator.assert_metric('dell_powerflex.avg_read_latency_in_microsec', value=latency, tags=tags)
        assert_bwc_metrics(aggregator, DEVICE_STATS_BWC_METRICS, tags)


def test_collect_system_with_name(dd_run_check, aggregator, instance, mock_http_get, mock_responses):
    mock_responses(f'{DEFAULT_GATEWAY_URL}/api/types/System/instances')[0]['name'] = 'my-powerflex'

    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    system_tags = BASE_TAGS + SYSTEM_TAGS + ['system_name:my-powerflex']
    aggregator.assert_metric('dell_powerflex.mdm_cluster.good_nodes', value=3, tags=system_tags)
    aggregator.assert_metric('dell_powerflex.mdm_cluster.good_replicas', value=2, tags=system_tags)


def test_include_filter_by_name(dd_run_check, aggregator, instance, mock_http_get, caplog):
    instance['resource_filters'] = [
        {'resource': 'storage_pool', 'property': 'name', 'patterns': ['^pool1$']},
    ]
    caplog.set_level(logging.DEBUG)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=1, tags=BASE_TAGS + POOL1_TAGS)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=BASE_TAGS + POOL2_TAGS)
    assert 'Skipping storage_pool storagepool2: did not match any include pattern' in caplog.text


def test_exclude_filter_by_name(dd_run_check, aggregator, instance, mock_http_get, caplog):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'type': 'exclude', 'patterns': ['^SDS3$']},
    ]
    caplog.set_level(logging.DEBUG)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=BASE_TAGS + SDS3_TAGS)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=1, tags=BASE_TAGS + SDS2_TAGS)
    assert 'Skipping sds SDS3: matched exclude pattern' in caplog.text


def test_exclude_takes_precedence_over_include(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'storage_pool', 'property': 'name', 'patterns': ['.*']},
        {'resource': 'storage_pool', 'property': 'name', 'type': 'exclude', 'patterns': ['^pool1$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=BASE_TAGS + POOL1_TAGS)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', tags=BASE_TAGS + POOL2_TAGS)


@pytest.mark.parametrize(
    'resource_filters',
    [
        pytest.param(
            [{'resource': 'sds', 'property': 'name', 'patterns': ['.*'], 'collect_statistics': False}],
            id='with_patterns',
        ),
        pytest.param(
            [{'resource': 'sds', 'property': 'name', 'collect_statistics': False}],
            id='without_patterns',
        ),
    ],
)
def test_collect_statistics_false(dd_run_check, aggregator, instance, mock_http_get, resource_filters):
    instance['resource_filters'] = resource_filters
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    sds3_tags = BASE_TAGS + SDS3_TAGS
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    aggregator.assert_metric('dell_powerflex.sds.count', value=1, tags=sds3_tags)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=sds3_tags)


def test_filter_by_volume_type(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'volume', 'property': 'volumeType', 'patterns': ['^ThinProvisioned$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.num_of_child_volumes', tags=BASE_TAGS + VOL_VOLUMEE_TAGS)
    aggregator.assert_metric('dell_powerflex.num_of_child_volumes', count=0, tags=BASE_TAGS + VOL_SNAP1_TAGS)


def test_unfiltered_resources_not_affected(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'patterns': ['^nonexistent$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=BASE_TAGS + SDS3_TAGS)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', tags=BASE_TAGS + POOL1_TAGS)


def test_multiple_filters_same_resource_type(dd_run_check, aggregator, instance, mock_http_get):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'patterns': ['^SDS[12]$']},
        {'resource': 'sds', 'property': 'id', 'type': 'exclude', 'patterns': ['^d1c062b800000001$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=1, tags=BASE_TAGS + SDS1_TAGS)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=BASE_TAGS + SDS2_TAGS)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=BASE_TAGS + SDS3_TAGS)


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


def test_invalid_filter_type_is_skipped(dd_run_check, aggregator, instance, mock_http_get):
    # test that a restrictive pattern with an invalid type is skipped
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'name', 'type': 'exculde', 'patterns': ['^nonexistent$']},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('dell_powerflex.sds.count', at_least=1)


def test_include_filter_missing_property(dd_run_check, aggregator, instance, mock_http_get, caplog):
    instance['resource_filters'] = [
        {'resource': 'sds', 'property': 'nonexistent_field', 'patterns': ['.*']},
    ]
    caplog.set_level(logging.DEBUG)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    aggregator.assert_metric('dell_powerflex.sds.count', count=0)
    assert 'property nonexistent_field not found' in caplog.text


@pytest.mark.parametrize(
    'resource_filters',
    [
        pytest.param(
            [{'resource': 'sds', 'property': 'nonexistent_field', 'type': 'exclude', 'patterns': ['.*']}],
            id='exclude_filter_missing_property',
        ),
        pytest.param(
            [{'resource': 'sds', 'property': 'name', 'patterns': [123, '.*']}],
            id='non_string_pattern_skipped',
        ),
    ],
)
def test_invalid_filter_still_collects_metrics(dd_run_check, aggregator, instance, mock_http_get, resource_filters):
    instance['resource_filters'] = resource_filters
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    sds3_tags = BASE_TAGS + SDS3_TAGS
    aggregator.assert_metric('dell_powerflex.sds.count', value=1, tags=sds3_tags)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', tags=sds3_tags)


@pytest.mark.parametrize(
    'resource, property, stats_metric',
    [
        ('volume', 'name', 'dell_powerflex.num_of_child_volumes'),
        ('storage_pool', 'name', 'dell_powerflex.capacity.in_use_in_kb'),
        ('protection_domain', 'name', 'dell_powerflex.capacity.in_use_in_kb'),
        ('sds', 'name', 'dell_powerflex.capacity.in_use_in_kb'),
        ('sdc', 'sdcType', 'dell_powerflex.num_of_mapped_volumes'),
        ('device', 'name', 'dell_powerflex.capacity.in_use_in_kb'),
    ],
)
def test_collect_statistics_false_per_resource(
    dd_run_check, aggregator, instance, mock_http_get, resource, property, stats_metric
):
    instance['resource_filters'] = [
        {'resource': resource, 'property': property, 'patterns': ['.*'], 'collect_statistics': False},
    ]
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    aggregator.assert_metric(f'dell_powerflex.{resource}.count', at_least=1)
    aggregator.assert_metric_has_tag(stats_metric, f'dell_type:{resource}', count=0)


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
    aggregator.assert_metric(f'dell_powerflex.{resource}.count', count=0)


def test_collect_events(dd_run_check, aggregator, instance, mock_http_get):
    instance['collect_events'] = True
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    events = aggregator.events
    # Fixture has 3 CRITICAL + 1 MAJOR + 1 MINOR; filter keeps CRITICAL and MAJOR only
    assert len(events) == 4
    for event in events:
        assert event['alert_type'] == 'error'
        assert event['event_type'] == 'dell_powerflex.event'
        assert event['source_type_name'] == 'dell-powerflex'
        assert f'powerflex_gateway_url:{DEFAULT_GATEWAY_URL}' in event['tags']

    severities = {tag for e in events for tag in e['tags'] if tag.startswith('severity:')}
    assert severities == {'severity:CRITICAL', 'severity:MAJOR'}

    titles = [e['msg_title'] for e in events]
    assert 'Health Check Failed' in titles
    assert 'Unknown Snmp Trap' in titles
    assert 'Postgres Instance Different Timeline' in titles

    health_check_event = next(e for e in events if e['msg_title'] == 'Health Check Failed')
    assert (
        'pfm-asmmanager: Health check failed: SDNAS Gateway pod failed to response.' in health_check_event['msg_text']
    )
    assert 'powerflex_event_name:HEALTH_CHECK_FAILED' in health_check_event['tags']
    assert 'category:AUDIT' in health_check_event['tags']
    assert 'domain:MANAGEMENT' in health_check_event['tags']
    assert 'service_name:pfm-asmmanager' in health_check_event['tags']

    major_event = next(e for e in events if 'severity:MAJOR' in e['tags'])
    assert major_event['msg_title'] == 'Postgres Instance Different Timeline'
    assert check.read_persistent_cache('last_event_timestamp') is not None


def test_collect_events_subsequent_run_uses_cached_time(dd_run_check, aggregator, instance, mock_http_get, mocker):
    instance['collect_events'] = True
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    cached_timestamp = check.read_persistent_cache('last_event_timestamp')
    spy = mocker.spy(check._api, 'get_events')
    dd_run_check(check)

    assert spy.call_args.kwargs['since'] == cached_timestamp


def test_collect_alerts_subsequent_run_uses_cached_time(dd_run_check, aggregator, instance, mock_http_get, mocker):
    instance['collect_alerts'] = True
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    cached_timestamp = check.read_persistent_cache('last_alert_timestamp')
    spy = mocker.spy(check._api, 'get_alerts')
    dd_run_check(check)

    assert spy.call_args.kwargs['since'] == cached_timestamp


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
    cache_key = 'last_event_timestamp' if config_key == 'collect_events' else 'last_alert_timestamp'
    dd_run_check(check)  # initialize persistent cache prefix
    previous_timestamp = '2020-01-01T00:00:00.000000Z'
    check.write_persistent_cache(cache_key, previous_timestamp)
    dd_run_check(check)
    assert log_message in caplog.text
    assert len(aggregator.events) == 0
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1)
    assert check.read_persistent_cache(cache_key) == previous_timestamp


@pytest.mark.parametrize(
    'config_key, mock_target, log_message',
    [
        (
            'collect_events',
            'datadog_checks.dell_powerflex.api.PowerFlexAPI.get_events',
            'Skipping malformed event',
        ),
        (
            'collect_alerts',
            'datadog_checks.dell_powerflex.api.PowerFlexAPI.get_alerts',
            'Skipping malformed alert',
        ),
    ],
)
def test_malformed_record_is_skipped(
    dd_run_check, aggregator, instance, mock_http_get, mocker, caplog, config_key, mock_target, log_message
):
    instance[config_key] = True
    valid_record = {'name': 'VALID_EVENT', 'timestamp': '2026-03-18T03:40:16.253Z', 'severity': 'CRITICAL'}
    malformed_record = {'name': 'BAD_EVENT', 'timestamp': 'not-a-timestamp', 'severity': 'CRITICAL'}
    mocker.patch(mock_target, return_value=[valid_record, malformed_record])
    caplog.set_level(logging.WARNING)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    assert log_message in caplog.text
    assert len(aggregator.events) == 1


def test_collect_alerts(dd_run_check, aggregator, instance, mock_http_get):
    instance['collect_alerts'] = True
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    alerts = aggregator.events
    assert len(alerts) == 2
    for alert in alerts:
        assert alert['event_type'] == 'dell_powerflex.alert'
        assert alert['source_type_name'] == 'dell-powerflex'
        assert f'powerflex_gateway_url:{DEFAULT_GATEWAY_URL}' in alert['tags']

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
    assert check.read_persistent_cache('last_alert_timestamp') is not None


def test_statistics_failure_does_not_block_other_resources(
    dd_run_check, aggregator, instance, mock_http_get, mocker, caplog
):
    sds2_stats = {'capacityInUseInKb': 350208, 'unusedCapacityInKb': 103406592, 'numOfDevices': 1}

    def selective_fail(sds_id):
        if sds_id == 'd1c062b700000000':
            raise Exception('stats API error')
        return sds2_stats

    mocker.patch(
        'datadog_checks.dell_powerflex.api.PowerFlexAPI.get_sds_statistics',
        side_effect=selective_fail,
    )
    caplog.set_level(logging.WARNING)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    assert 'Failed to collect statistics for d1c062b700000000' in caplog.text

    # SDS3 (d1c062b700000000) inventory metric should exist but stats should be missing
    sds3_tags = BASE_TAGS + SDS3_TAGS
    aggregator.assert_metric('dell_powerflex.sds.count', value=1, tags=sds3_tags)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', count=0, tags=sds3_tags)

    # SDS2 (d1c062b800000001) stats should still be collected
    sds2_tags = BASE_TAGS + SDS2_TAGS
    aggregator.assert_metric('dell_powerflex.sds.count', value=1, tags=sds2_tags)
    aggregator.assert_metric('dell_powerflex.capacity.in_use_in_kb', value=350208, tags=sds2_tags)


def test_user_configured_tags(dd_run_check, aggregator, instance, mock_http_get):
    instance['tags'] = ['env:prod', 'cluster:powerflex-01']
    instance['collect_events'] = True
    instance['collect_alerts'] = True
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    custom_tags = ['env:prod', 'cluster:powerflex-01']
    base_tags = BASE_TAGS + custom_tags

    # Verify metrics include user-configured tags
    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1, tags=base_tags)
    aggregator.assert_metric('dell_powerflex.system.count', value=1, tags=base_tags + SYSTEM_TAGS)
    aggregator.assert_metric('dell_powerflex.storage_pool.count', value=1, tags=base_tags + POOL1_TAGS)

    # Verify events include user-configured tags
    for event in aggregator.events:
        for tag in custom_tags:
            assert tag in event['tags'], f"Expected tag '{tag}' in event tags: {event['tags']}"
