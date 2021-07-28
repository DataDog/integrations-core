# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import mock

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.ibm_i import IbmICheck
from datadog_checks.ibm_i.check import SystemInfo


def test_check(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = IbmICheck('ibm_i', {}, [instance])
    check.check(instance)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_fetch_system_info(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.execute_query', return_value=[("hostname", "7", "3")]), mock.patch(
        'datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess'
    ) as delete_conn:
        system_info = check.fetch_system_info()

    assert system_info == SystemInfo(hostname="hostname", os_version=7, os_release=3)
    delete_conn.assert_not_called()
    check.log.assert_not_called()


def test_failed_fetch_system_info(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.execute_query', return_value=[]), mock.patch(
        'datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess'
    ) as delete_conn:
        system_info = check.fetch_system_info()

    assert system_info is None
    delete_conn.assert_not_called()
    check.log.error.assert_called_once()


def test_query_error_system_info(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    exc = Exception("boom")
    with mock.patch('datadog_checks.ibm_i.IbmICheck.execute_query', side_effect=exc):
        system_info = check.fetch_system_info()

    assert system_info is None
    check.log.error.assert_not_called()


def test_set_up_query_manager_error(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=None):
        check.set_up_query_manager()
    assert check._query_manager is None


def test_set_up_query_manager_7_2(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch(
        'datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 2)
    ), mock.patch('datadog_checks.ibm_i.IbmICheck.ibm_mq_check', return_value=True):
        check.set_up_query_manager()
    assert check._query_manager is not None
    assert len(check._query_manager.queries) == 9


def test_set_up_query_manager_7_2_no_ibm_mq(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch(
        'datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 2)
    ), mock.patch('datadog_checks.ibm_i.IbmICheck.ibm_mq_check', return_value=False):
        check.set_up_query_manager()
    assert check._query_manager is not None
    assert len(check._query_manager.queries) == 8


def test_set_up_query_manager_7_4(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch(
        'datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 4)
    ), mock.patch('datadog_checks.ibm_i.IbmICheck.ibm_mq_check', return_value=True):
        check.set_up_query_manager()
    assert check._query_manager is not None
    assert len(check._query_manager.queries) == 11


def test_set_up_query_manager_7_4_no_ibm_mq(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch(
        'datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 4)
    ), mock.patch('datadog_checks.ibm_i.IbmICheck.ibm_mq_check', return_value=False):
        check.set_up_query_manager()
    assert check._query_manager is not None
    assert len(check._query_manager.queries) == 10


def test_check_no_query_manager(aggregator, instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=None):
        check.check(instance)
    assert check._query_manager is None
    check.log.warning.assert_called_once()
    aggregator.assert_all_metrics_covered()


def test_check_query_error(aggregator, instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()

    with mock.patch(
        'datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 4)
    ), mock.patch('datadog_checks.ibm_i.IbmICheck.execute_query', side_effect=Exception("boom")):
        check.check(instance)
    assert check._query_manager is not None
    aggregator.assert_service_check("ibm_i.can_connect", count=1, status=AgentCheck.CRITICAL)
    aggregator.assert_metric("ibm_i.check.duration", hostname="host", tags=["check_id:{}".format(check.check_id)])
    aggregator.assert_all_metrics_covered()
