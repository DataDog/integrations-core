# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from pymongo.errors import ConnectionFailure

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
@mock.patch('pymongo.database.Database.command')
def test_emits_ok_service_check_when_service_is_up(mock_command, dd_run_check, aggregator, instance):
    check = TddCheck('tdd', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('tdd.can_connect', TddCheck.OK)
    mock_command.assert_has_calls([mock.call('ping')])
