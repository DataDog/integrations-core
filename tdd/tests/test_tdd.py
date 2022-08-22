# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from pymongo.errors import ConnectionFailure

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tdd import TddCheck


@pytest.mark.unit
@mock.patch('datadog_checks.tdd.check.MongoClient')
def test_check(mocked_mongo_client, dd_run_check, aggregator, instance):
    # Given
    check = TddCheck('tdd', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
@mock.patch('datadog_checks.tdd.check.MongoClient')
def test_emits_critical_service_check_when_service_is_down(mocked_mongo_client, dd_run_check, aggregator, instance):
    # Given
    check = TddCheck('tdd', {}, [instance])
    mocked_mongo_client().admin.command.side_effect = ConnectionFailure('Service not available')
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('tdd.can_connect', TddCheck.CRITICAL)


@pytest.mark.unit
@mock.patch('datadog_checks.tdd.check.MongoClient')
def test_emits_ok_service_check_when_service_is_up(mocked_mongo_client, dd_run_check, aggregator, instance):
    # Given
    check = TddCheck('tdd', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('tdd.can_connect', TddCheck.OK)
