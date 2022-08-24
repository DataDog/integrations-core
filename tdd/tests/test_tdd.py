# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from pymongo.errors import ConnectionFailure

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tdd import TddCheck


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
@mock.patch('pymongo.database.Database.command', side_effect=[{'ok': 1}, {'parsed': {}}])
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
    mock_command.assert_has_calls([mock.call('ping'), mock.call('serverStatus')])


@pytest.mark.unit
@mock.patch('pymongo.database.Database.command', side_effect=[{'ok': 1}, {'uptime': 3600}])
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
def test_emits_metrics_when_service_is_up(mock_server_info, mock_command, dd_run_check, aggregator, instance):
    # Given
    check = TddCheck('tdd', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_metric('tdd.uptime')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    mock_command.assert_has_calls([mock.call('ping'), mock.call('serverStatus')])
