# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict  # noqa: F401

import mock

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.ibm_i import IbmICheck
from datadog_checks.ibm_i.check import SystemInfo


def test_check(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = IbmICheck('ibm_i', {}, [instance])
    check.check(instance)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_cancel(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.load_configuration_models()

    with mock.patch('datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess') as m:
        check.cancel()
    m.assert_called_once()


def test_connection_subprocess(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.load_configuration_models()
    with mock.patch('datadog_checks.ibm_i.IbmICheck._create_connection_subprocess') as m:
        check.connection_subprocess
        check._subprocess = mock.MagicMock()
        check.connection_subprocess
    m.assert_called_once()


def test_execute_query(instance):
    """Check that execute_query reads and parses the process stdout."""
    check = IbmICheck('ibm_i', {}, [instance])
    check.load_configuration_models()
    check._subprocess = mock.MagicMock()
    check._subprocess.stdout = mock.MagicMock()
    check._subprocess.stdout.readline = mock.MagicMock(return_value='{"a": "b"}')
    assert next(check.execute_query({'text': 'query', 'timeout': 2})) == {'a': 'b'}


def test_connnection_string_no_fields(instance):
    instance = {
        **instance,
        **{
            'driver': 'driver',
        },
    }
    check = IbmICheck('ibm_i', {}, [instance])
    check.load_configuration_models()
    assert check.connection_string == 'Driver={driver};'


def test_connnection_string(instance):
    instance = {
        **instance,
        **{
            'driver': 'driver',
            'system': 'system',
            'username': 'username',
            'password': 'password',
        },
    }
    check = IbmICheck('ibm_i', {}, [instance])
    check.load_configuration_models()
    assert check.connection_string == 'Driver={driver};System=system;UID=username;PWD=password;'


def test_connnection_string_defined(instance):
    instance = {
        **instance,
        **{
            'connection_string': 'constring',
            'driver': 'driver',
            'system': 'system',
            'username': 'username',
            'password': 'password',
        },
    }
    check = IbmICheck('ibm_i', {}, [instance])
    check.load_configuration_models()
    assert check.connection_string == 'constring'
    check._connection_string = 'modified'
    assert check.connection_string == 'modified'


def test_fetch_system_info(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.execute_query', return_value=[("hostname", "7", "3")]), mock.patch(
        'datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess'
    ) as delete_conn:
        system_info = check.fetch_system_info()

    assert system_info == SystemInfo(hostname="hostname", os_version=7, os_release=3)
    delete_conn.assert_not_called()
    check.log.assert_not_called()


def test_fetch_system_info_too_many(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.execute_query', return_value=[1, 2]), mock.patch(
        'datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess'
    ) as delete_conn:
        system_info = check.fetch_system_info()

    assert system_info is None
    delete_conn.assert_not_called()
    check.log.error.assert_called_once()


def test_fetch_system_info_incorrect_schema(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.execute_query', return_value=[[]]), mock.patch(
        'datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess'
    ) as delete_conn:
        system_info = check.fetch_system_info()

    assert system_info is None
    delete_conn.assert_not_called()
    check.log.error.assert_called_once()


def test_fetch_system_info_incorrect_version(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch(
        'datadog_checks.ibm_i.IbmICheck.execute_query', return_value=[["hostname", "invalid", 3]]
    ), mock.patch('datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess') as delete_conn:
        system_info = check.fetch_system_info()

    assert system_info is None
    delete_conn.assert_not_called()
    check.log.error.assert_called_once()


def test_fetch_system_info_incorrect_release(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch(
        'datadog_checks.ibm_i.IbmICheck.execute_query', return_value=[["hostname", 7, "invalid"]]
    ), mock.patch('datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess') as delete_conn:
        system_info = check.fetch_system_info()

    assert system_info is None
    delete_conn.assert_not_called()
    check.log.error.assert_called_once()


def test_failed_fetch_system_info(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
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
    check.load_configuration_models()
    exc = Exception("boom")
    with mock.patch('datadog_checks.ibm_i.IbmICheck.execute_query', side_effect=exc):
        system_info = check.fetch_system_info()

    assert system_info is None
    check.log.error.assert_called_once()


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
    with mock.patch('datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 2)):
        check.set_up_query_manager()
    assert check._query_manager is not None
    assert check._query_manager.hostname == "host"
    assert len(check._query_manager.queries) == 8


def test_set_up_query_manager_7_4(instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 4)):
        check.set_up_query_manager()
    assert check._query_manager is not None
    assert check._query_manager.hostname == "host"
    assert len(check._query_manager.queries) == 10


def test_set_up_query_manager_7_4_hostname(instance):
    instance = {
        **instance,
        **{'hostname': 'overridden-hostname'},
    }
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 4)):
        check.set_up_query_manager()
    assert check._query_manager is not None
    assert check._query_manager.hostname == "overridden-hostname"
    assert len(check._query_manager.queries) == 10


def test_set_up_query_manager_7_4_queries_list(instance):
    instance = {
        **instance,
        **{
            'queries': [
                {'name': 'disk_usage'},
                {'name': 'cpu_usage'},
                {'name': 'job_memory_usage'},
                {'name': 'memory_info'},
                {'name': 'subsystem'},
                {'name': 'job_queue'},
                {'name': 'message_queue_info'},
            ]
        },
    }
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 4)):
        check.set_up_query_manager()
    assert check._query_manager is not None
    # disk usage counts like 2, the rest (6 queries) count as 1
    assert len(check._query_manager.queries) == 6 + 2


def test_set_up_query_manager_7_2_queries_list(instance):
    instance = {
        **instance,
        **{
            'queries': [
                {'name': 'disk_usage'},
                {'name': 'cpu_usage'},
                {'name': 'job_memory_usage'},
                {'name': 'memory_info'},
                {'name': 'subsystem'},
                {'name': 'job_queue'},
                {'name': 'message_queue_info'},
            ]
        },
    }
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.fetch_system_info', return_value=SystemInfo("host", 7, 2)):
        check.set_up_query_manager()
    assert check._query_manager is not None
    # disk_usage counts like 1, subsystem like 0 (not available on 7.2), the rest (5 queries) count as 1
    assert len(check._query_manager.queries) == 5 + 0 + 1


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
        assert check._query_manager is None
        check.check(instance)
        assert check._query_manager is not None
        assert check._query_manager.hostname == "host"
        check.check(instance)
    aggregator.assert_service_check("ibm_i.can_connect", count=2, status=AgentCheck.CRITICAL)
    aggregator.assert_all_metrics_covered()
