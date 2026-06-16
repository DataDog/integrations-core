# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
import time
from copy import deepcopy
from typing import Any

import ibm_db
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.ibm_db2 import IbmDb2Check

from . import metrics


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_standard(aggregator, instance):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check(instance)

    _assert_standard(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    _assert_standard(aggregator)


@pytest.mark.e2e
def test_dbm_e2e(dd_agent_check: Any, instance: dict[str, Any]) -> None:
    dbm_instance = deepcopy(instance)
    dbm_instance.update(
        {
            'dbm': True,
            'query_metrics': {'enabled': True, 'run_sync': True, 'collection_interval': 0.1},
            'query_samples': {
                'enabled': True,
                'run_sync': True,
                'collection_interval': 0.1,
                'explained_queries_per_hour_per_query': 3600,
                'samples_per_hour_per_query': 3600,
            },
            'query_activity': {'enabled': True, 'run_sync': True, 'collection_interval': 0.1},
            'collect_settings': {'enabled': True, 'run_sync': True, 'collection_interval': 0.1},
            'collect_schemas': {'enabled': False},
            'database_instance_collection_interval': 0.1,
            'database_identifier': {'template': '$resolved_hostname:$db'},
        }
    )

    stop_workload = threading.Event()
    workload_errors: list[BaseException] = []
    workload_thread = threading.Thread(
        target=_run_query_metrics_workload, args=(instance, stop_workload, workload_errors)
    )
    table_name = 'DBM_E2E_LOCK'
    _drop_table_if_exists(instance, table_name)
    _execute_statement_no_fetch(instance, f'CREATE TABLE {table_name} (id INTEGER NOT NULL PRIMARY KEY)')
    _execute_statement_no_fetch(instance, f'INSERT INTO {table_name} VALUES (1)')

    blocker = _open_connection(instance)
    ibm_db.autocommit(blocker, ibm_db.SQL_AUTOCOMMIT_OFF)
    blocker_cursor = ibm_db.exec_immediate(blocker, f'UPDATE {table_name} SET id = id WHERE id = 1')
    blocked_errors: list[BaseException] = []
    blocked_thread = threading.Thread(
        target=_execute_blocked_statement,
        args=(instance, f'UPDATE {table_name} SET id = id WHERE id = 1', blocked_errors),
    )

    try:
        workload_thread.start()
        blocked_thread.start()
        time.sleep(1)

        aggregator = dd_agent_check(dbm_instance, check_times=2)

        assert not workload_errors
        assert not blocked_errors

        metrics_events = aggregator.get_event_platform_events('dbm-metrics')
        assert metrics_events
        assert any(event.get('db2_rows') for event in metrics_events)

        sample_events = aggregator.get_event_platform_events('dbm-samples')
        assert any(event.get('dbm_type') == 'fqt' for event in sample_events)
        assert any(event.get('dbm_type') == 'plan' for event in sample_events)

        activity_events = aggregator.get_event_platform_events('dbm-activity')
        assert activity_events
        assert any(event.get('db2_activity') for event in activity_events)

        metadata_events = aggregator.get_event_platform_events('dbm-metadata')
        database_instance_events = [event for event in metadata_events if event.get('kind') == 'database_instance']
        assert database_instance_events, metadata_events
        assert database_instance_events[0]['metadata']['dbm'] is True
        assert any(event.get('kind') == 'db2_settings' for event in metadata_events)
    finally:
        stop_workload.set()
        workload_thread.join(timeout=10)
        assert not workload_thread.is_alive()
        ibm_db.rollback(blocker)
        ibm_db.free_result(blocker_cursor)
        ibm_db.close(blocker)
        blocked_thread.join(timeout=10)
        assert not blocked_thread.is_alive()
        _drop_table_if_exists(instance, table_name)


def _assert_standard(aggregator):
    aggregator.assert_service_check('ibm_db2.can_connect', AgentCheck.OK)

    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')
    for metric in metrics.OPTIONAL_STANDARD:
        if aggregator.metrics(metric):
            aggregator.assert_metric_has_tag(metric, 'db:datadog')
            aggregator.assert_metric_has_tag(metric, 'foo:bar')
        else:
            aggregator.assert_metric_has_tag(metric, 'db:datadog', at_least=0)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def _run_query_metrics_workload(
    instance: dict[str, Any], stop_workload: threading.Event, errors: list[BaseException]
) -> None:
    connection = _open_connection(instance)
    statement = ibm_db.prepare(connection, 'VALUES 1357911')
    try:
        while not stop_workload.is_set():
            ibm_db.execute(statement)
            ibm_db.fetch_tuple(statement)
            time.sleep(0.05)
    except BaseException as e:
        errors.append(e)
    finally:
        ibm_db.free_result(statement)
        ibm_db.close(connection)


def _execute_blocked_statement(instance: dict[str, Any], query: str, errors: list[BaseException]) -> None:
    try:
        _execute_statement_no_fetch(instance, query)
    except BaseException as e:
        errors.append(e)


def _execute_statement_no_fetch(instance: dict[str, Any], query: str) -> None:
    connection = _open_connection(instance)
    try:
        cursor = ibm_db.exec_immediate(connection, query)
        ibm_db.free_result(cursor)
    finally:
        ibm_db.close(connection)


def _drop_table_if_exists(instance: dict[str, Any], table_name: str) -> None:
    try:
        _execute_statement_no_fetch(instance, f'DROP TABLE {table_name}')
    except Exception:
        pass


def _open_connection(instance: dict[str, Any]) -> Any:
    target, username, password = IbmDb2Check.get_connection_data(
        instance['db'],
        instance['username'],
        instance['password'],
        instance['host'],
        instance['port'],
        'none',
        None,
        None,
    )
    return ibm_db.connect(target, username, password, {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER})
