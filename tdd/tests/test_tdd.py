# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from pymongo.errors import ConnectionFailure

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tdd import TddCheck

from . import common


@pytest.mark.unit
@mock.patch('pymongo.database.Database.command', side_effect=ConnectionFailure('Service not available'))
def test_emits_critical_service_check_when_service_is_down(mock_command, dd_run_check, aggregator, instance):
    # Given
    check = TddCheck('tdd', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('tdd.can_connect', TddCheck.CRITICAL)
    mock_command.assert_has_calls([mock.call('ping')])


@pytest.mark.unit
@mock.patch('pymongo.database.Database.command', return_value={'ok': 0})
def test_emits_critical_service_check_when_service_is_up_but_ping_returns_0(
    mock_command, dd_run_check, aggregator, instance
):
    # Given
    check = TddCheck('tdd', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('tdd.can_connect', TddCheck.CRITICAL)
    mock_command.assert_has_calls([mock.call('ping')])


@pytest.mark.unit
@mock.patch('pymongo.database.Database.command', return_value={'ok': 1})
def test_emits_ok_service_check_when_service_is_up_and_ping_returns_1(mock_command, dd_run_check, aggregator, instance):
    # Given
    check = TddCheck('tdd', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('tdd.can_connect', TddCheck.OK)
    mock_command.assert_has_calls([mock.call('ping')])


@pytest.mark.unit
@mock.patch('pymongo.database.Database.command', side_effect=[{'ok': 1}, {}])
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
def test_version_metadata(mock_server_info, mock_command, dd_run_check, datadog_agent, instance):
    # Given
    check = TddCheck('tdd', {}, [instance])
    check.check_id = 'test:123'
    # When
    dd_run_check(check)
    # Then
    datadog_agent.assert_metadata(
        'test:123',
        {
            'version.scheme': 'semver',
            'version.major': '5',
            'version.minor': '0',
            'version.patch': '0',
            'version.raw': '5.0.0',
        },
    )
    mock_command.assert_has_calls([mock.call('ping'), mock.call('serverStatus', tcmalloc=0)])
    mock_server_info.assert_called_once()


@pytest.mark.unit
@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'ok': 1},
        {
            'uptime': 3600,
            'asserts': {'regular': 0, 'warning': 0, 'msg': 0, 'user': 27, 'rollovers': 0},
            'backgroundFlushing': {
                'flushes': 10,
                'total_ms': 123456789,
                'average_ms': 123,
                'last_ms': 123,
                'last_finished': {'$date': 1600245226383},
            },
        },
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
def test_emits_server_status_without_tcmalloc_metrics_when_service_is_up(
    mock_server_info, mock_command, dd_run_check, aggregator, instance
):
    # Given
    expected_metrics = common.SERVER_STATUS_METRICS
    not_expected_metrics = common.TCMALLOC_METRICS
    check = TddCheck('tdd', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
    for metric in not_expected_metrics:
        aggregator.assert_metric(metric, count=0)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    mock_command.assert_has_calls([mock.call('ping'), mock.call('serverStatus', tcmalloc=0)])
    mock_server_info.assert_called_once()


@pytest.mark.unit
@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'ok': 1},
        {
            'uptime': 3600,
            'asserts': {'regular': 0, 'warning': 0, 'msg': 0, 'user': 27, 'rollovers': 0},
            'backgroundFlushing': {
                'flushes': 10,
                'total_ms': 123456789,
                'average_ms': 123,
                'last_ms': 123,
                'last_finished': {'$date': 1600245226383},
            },
            'tcmalloc': {
                'generic': {'current_allocated_bytes': 93292896, 'heap_size': 95100928},
                'tcmalloc': {
                    'pageheap_free_bytes': 491520,
                    'pageheap_unmapped_bytes': 0,
                    'max_total_thread_cache_bytes': 1028653056,
                    'current_total_thread_cache_bytes': 818680,
                    'total_free_bytes': 1316512,
                    'central_cache_free_bytes': 274984,
                    'transfer_cache_free_bytes': 222848,
                    'thread_cache_free_bytes': 818680,
                    'aggressive_memory_decommit': 0,
                    'pageheap_committed_bytes': 95100928,
                    'pageheap_scavenge_count': 0,
                    'pageheap_commit_count': 56,
                    'pageheap_total_commit_bytes': 95100928,
                    'pageheap_decommit_count': 0,
                    'pageheap_total_decommit_bytes': 0,
                    'pageheap_reserve_count': 56,
                    'pageheap_total_reserve_bytes': 95100928,
                    'spinlock_total_delay_ns': 350667,
                    'release_rate': 1.0,
                },
            },
        },
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
def test_emits_server_status_with_tcmalloc_metrics_when_service_is_up(
    mock_server_info, mock_command, dd_run_check, aggregator, instance
):
    # Given
    expected_metrics = common.SERVER_STATUS_METRICS.union(common.TCMALLOC_METRICS)
    instance['additional_metrics'] = ['tcmalloc']
    check = TddCheck('tdd', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    mock_command.assert_has_calls([mock.call('ping'), mock.call('serverStatus', tcmalloc=1)])
    mock_server_info.assert_called_once()
