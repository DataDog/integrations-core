# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
import time
from copy import deepcopy
from typing import Any

import ibm_db
import pytest

from datadog_checks.base.utils.serialization import json
from datadog_checks.ibm_db2 import IbmDb2Check

from . import metrics
from .common import CONFIG, DB2_VERSION, DBM_USERNAME

CHECK_ID = 'test:123'

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures('dd_environment')
def test_bad_config(aggregator, instance, dd_run_check):
    instance['port'] = '60000'
    instance["connection_timeout"] = 1
    check = IbmDb2Check('ibm_db2', {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check(check.SERVICE_CHECK_CONNECT, check.CRITICAL)


@pytest.mark.usefixtures('dd_environment')
def test_buffer_pool_tags(aggregator, instance, dd_run_check):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    dd_run_check(check)

    for metric in metrics.BUFFERPOOL:
        aggregator.assert_metric_has_tag_prefix(metric, 'bufferpool:')
    aggregator.assert_service_check(check.SERVICE_CHECK_CONNECT, count=1, status=check.OK)


@pytest.mark.usefixtures('dd_environment')
def test_table_space_tags(aggregator, instance, dd_run_check):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    dd_run_check(check)

    for metric in metrics.TABLESPACE:
        aggregator.assert_metric_has_tag_prefix(metric, 'tablespace:')
    aggregator.assert_service_check(check.SERVICE_CHECK_CONNECT, count=1, status=check.OK)


@pytest.mark.usefixtures('dd_environment')
def test_table_space_state_change(aggregator, instance, dd_run_check):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._table_space_states['USERSPACE1'] = 'test'
    dd_run_check(check)

    aggregator.assert_event('State of `USERSPACE1` changed from `test` to `NORMAL`.')
    aggregator.assert_service_check(check.SERVICE_CHECK_CONNECT, count=1, status=check.OK)


@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance, dd_run_check):
    instance['custom_queries'] = [
        {
            'metric_prefix': 'ibm_db2',
            'tags': ['test:ibm_db2'],
            'query': 'SELECT files_closed, tbsp_name FROM TABLE(MON_GET_TABLESPACE(NULL, -1))',
            'columns': [
                {'name': 'tablespace.files_closed', 'type': 'monotonic_count'},
                {'name': 'tablespace', 'type': 'tag'},
            ],
        }
    ]

    check = IbmDb2Check('ibm_db2', {}, [instance])
    dd_run_check(check)

    # There is also `SYSTOOLSPACE` but it seems that takes some time to come up
    table_spaces = ['USERSPACE1', 'TEMPSPACE1', 'SYSCATSPACE']

    for table_space in table_spaces:
        aggregator.assert_metric(
            'ibm_db2.tablespace.files_closed',
            metric_type=3,
            tags=['db:datadog', 'foo:bar', 'test:ibm_db2', 'tablespace:{}'.format(table_space)],
        )
    aggregator.assert_service_check(check.SERVICE_CHECK_CONNECT, count=1, status=check.OK)


@pytest.mark.usefixtures('dd_environment')
def test_custom_queries_init_config(aggregator, instance, dd_run_check):
    init_config = {
        'global_custom_queries': [
            {
                'metric_prefix': 'ibm_db2',
                'tags': ['test:ibm_db2'],
                'query': 'SELECT files_closed, tbsp_name FROM TABLE(MON_GET_TABLESPACE(NULL, -1))',
                'columns': [
                    {'name': 'tablespace.files_closed', 'type': 'monotonic_count'},
                    {'name': 'tablespace', 'type': 'tag'},
                ],
            }
        ]
    }

    check = IbmDb2Check('ibm_db2', init_config, [instance])
    dd_run_check(check)

    # There is also `SYSTOOLSPACE` but it seems that takes some time to come up
    table_spaces = ['USERSPACE1', 'TEMPSPACE1', 'SYSCATSPACE']

    for table_space in table_spaces:
        aggregator.assert_metric(
            'ibm_db2.tablespace.files_closed',
            metric_type=3,
            tags=['db:datadog', 'foo:bar', 'test:ibm_db2', 'tablespace:{}'.format(table_space)],
        )
    aggregator.assert_service_check(check.SERVICE_CHECK_CONNECT, count=1, status=check.OK)


@pytest.mark.usefixtures('dd_environment')
def test_metadata(instance, datadog_agent, dd_run_check):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check_id = CHECK_ID

    dd_run_check(check)

    # only major and minor are consistent values
    major, minor = DB2_VERSION.split('.')[:2]

    version_metadata = {
        'version.scheme': 'ibm_db2',
        'version.major': major,
        'version.minor': minor,
    }

    datadog_agent.assert_metadata(CHECK_ID, version_metadata)


@pytest.mark.usefixtures('dd_environment')
def test_dbm_query_metrics(aggregator, dbm_instance: dict) -> None:
    check = IbmDb2Check('ibm_db2', {}, [dbm_instance])
    check._dbms_version = DB2_VERSION
    query = 'VALUES 1357911'

    connection = _open_connection(dbm_instance)
    statement = ibm_db.prepare(connection, query)
    try:
        ibm_db.execute(statement)
        ibm_db.fetch_tuple(statement)
        check.statement_metrics.run_job()

        ibm_db.execute(statement)
        ibm_db.fetch_tuple(statement)
        aggregator.reset()
        check.statement_metrics.run_job()
    finally:
        ibm_db.free_result(statement)
        ibm_db.close(connection)

    events = aggregator.get_event_platform_events('dbm-metrics')
    assert events
    event = events[0]
    assert event['database_instance'] == check.database_identifier
    assert event['db2_version'] == DB2_VERSION
    assert event['db2_rows']
    assert any(row['num_exec_with_metrics'] > 0 for row in event['db2_rows'])
    assert all('stmt_text' not in row for row in event['db2_rows'])

    sample_events = aggregator.get_event_platform_events('dbm-samples')
    assert sample_events
    assert sample_events[0]['ddsource'] == 'db2'
    assert sample_events[0]['dbm_type'] == 'fqt'


@pytest.mark.usefixtures('dd_environment')
def test_dbm_execution_plans(aggregator, dbm_instance: dict) -> None:
    dbm_instance['query_metrics'] = {'enabled': False, 'run_sync': True, 'collection_interval': 0.1}
    dbm_instance['query_activity'] = {'enabled': False}
    dbm_instance['collect_settings'] = {'enabled': False}
    dbm_instance['query_samples'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
        'explain_schema': DBM_USERNAME,
        'explained_queries_per_hour_per_query': 3600,
        'samples_per_hour_per_query': 3600,
    }
    check = IbmDb2Check('ibm_db2', {}, [dbm_instance])
    check._dbms_version = DB2_VERSION
    query = 'VALUES 246813579'

    connection = _open_connection(dbm_instance)
    statement = ibm_db.prepare(connection, query)
    try:
        ibm_db.execute(statement)
        ibm_db.fetch_tuple(statement)
        check.statement_metrics.run_job()

        ibm_db.execute(statement)
        ibm_db.fetch_tuple(statement)
        aggregator.reset()
        check.statement_metrics.run_job()
    finally:
        ibm_db.free_result(statement)
        ibm_db.close(connection)

    all_plan_events = [
        event for event in aggregator.get_event_platform_events('dbm-samples') if event['dbm_type'] == 'plan'
    ]
    plan_events = [event for event in all_plan_events if event['db']['statement'].upper().startswith('VALUES')]
    assert plan_events, [
        (event['db']['statement'], event['db']['plan']['collection_errors']) for event in all_plan_events
    ]

    event = plan_events[0]
    assert event['database_instance'] == check.database_identifier
    assert event['ddsource'] == 'db2'
    assert event['db2_version'] == DB2_VERSION
    assert event['db']['plan']['definition'], event['db']['plan']['collection_errors']
    assert event['db']['plan']['signature']
    assert event['db']['plan']['collection_errors'] is None
    assert 'Plan' in json.loads(event['db']['plan']['definition'])
    assert event['db2']['executable_id']
    assert event['db2']['explain_schema'] == DBM_USERNAME.upper()


@pytest.mark.usefixtures('dd_environment')
def test_dbm_settings_metadata(aggregator, dbm_instance: dict) -> None:
    dbm_instance['query_metrics'] = {'enabled': False}
    dbm_instance['collect_settings'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    check = IbmDb2Check('ibm_db2', {}, [dbm_instance])
    check._dbms_version = DB2_VERSION

    check.dbm_metadata.run_job()

    events = aggregator.get_event_platform_events('dbm-metadata')
    event = next(event for event in events if event['kind'] == 'db2_settings')
    assert event['database_instance'] == check.database_identifier
    assert event['metadata']
    assert any(row['name'].lower() == 'mon_act_metrics' for row in event['metadata'])
    assert any(row['config_scope'] == 'db' for row in event['metadata'])
    assert any(row['config_scope'] == 'dbm' for row in event['metadata'])
    assert all('pending_change' in row for row in event['metadata'])
    assert all(not tag.startswith('db:') for tag in event['tags'])


@pytest.mark.usefixtures('dd_environment')
def test_dbm_query_activity(aggregator, dbm_instance: dict) -> None:
    dbm_instance['query_metrics'] = {'enabled': False}
    dbm_instance['collect_settings'] = {'enabled': False}
    dbm_instance['query_activity'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    check = IbmDb2Check('ibm_db2', {}, [dbm_instance])
    check._dbms_version = DB2_VERSION

    instance = deepcopy(CONFIG)
    table_name = 'DBM_ACTIVITY_LOCK'
    _drop_table_if_exists(instance, table_name)
    _execute_statement_no_fetch(instance, f'CREATE TABLE {table_name} (id INTEGER NOT NULL PRIMARY KEY)')
    _execute_statement_no_fetch(instance, f'INSERT INTO {table_name} VALUES (1)')

    blocker = _open_connection(instance)
    ibm_db.autocommit(blocker, ibm_db.SQL_AUTOCOMMIT_OFF)
    blocker_cursor = ibm_db.exec_immediate(blocker, f'UPDATE {table_name} SET id = id WHERE id = 1')

    errors: list[BaseException] = []

    def run_blocked_statement() -> None:
        try:
            _execute_statement_no_fetch(instance, f'UPDATE {table_name} SET id = id WHERE id = 1')
        except BaseException as e:
            errors.append(e)

    blocked_statement = threading.Thread(target=run_blocked_statement)
    blocked_statement.start()

    try:
        events = []
        for _ in range(16):
            time.sleep(0.5)
            aggregator.reset()
            check.statement_samples.run_job()
            events = aggregator.get_event_platform_events('dbm-activity')
            if events and events[0]['db2_activity']:
                break

        assert not errors
        assert events

        event = events[0]
        assert event['database_instance'] == check.database_identifier
        assert event['ddsource'] == 'db2'
        assert event['dbm_type'] == 'activity'
        assert event['db2_version'] == DB2_VERSION
        assert isinstance(event['ddtags'], list)
        assert 'db2_connections' in event
        assert event['db2_activity']
        assert all('stmt_text' not in row for row in event['db2_activity'])
        assert all(row.get('query_signature') for row in event['db2_activity'])
        assert any(table_name in row.get('statement', '').upper() for row in event['db2_activity'])
    finally:
        ibm_db.rollback(blocker)
        ibm_db.free_result(blocker_cursor)
        ibm_db.close(blocker)
        blocked_statement.join(timeout=10)
        assert not blocked_statement.is_alive()
        _drop_table_if_exists(instance, table_name)


@pytest.mark.usefixtures('dd_environment')
def test_dbm_schema_metadata(aggregator, dbm_instance: dict) -> None:
    schema_name = 'DBM_SCHEMA'
    instance = deepcopy(CONFIG)
    _drop_schema_fixture(instance, schema_name)

    dbm_instance['query_metrics'] = {'enabled': False}
    dbm_instance['query_activity'] = {'enabled': False}
    dbm_instance['collect_settings'] = {'enabled': False}
    dbm_instance['collect_schemas'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
        'include_schemas': [schema_name],
        'max_columns': 10,
    }
    check = IbmDb2Check('ibm_db2', {}, [dbm_instance])
    check._dbms_version = DB2_VERSION

    try:
        _create_schema_fixture(instance, schema_name)
        check.dbm_metadata.run_job()

        events = [
            event for event in aggregator.get_event_platform_events('dbm-metadata') if event['kind'] == 'db2_databases'
        ]
        assert events

        event = events[0]
        assert event['database_instance'] == check.database_identifier
        assert event['dbms'] == 'db2'
        assert event['dbms_version'] == DB2_VERSION
        assert event['collection_payloads_count'] == len(events)
        assert event['collection_started_at']

        tables = {
            database['schemas'][0]['tables'][0]['name']: database['schemas'][0]['tables'][0]
            for schema_event in events
            for database in schema_event['metadata']
            if database['schemas'][0]['tables']
        }
        assert {'PARENT', 'CHILD'} <= set(tables)
        assert any(column['name'] == 'PARENT_ID' for column in tables['CHILD']['columns'])
        assert any(index['name'] == 'CHILD_PARENT_IDX' for index in tables['CHILD']['indexes'])
        assert any(
            foreign_key['referenced_table'] == '{}.PARENT'.format(schema_name)
            for foreign_key in tables['CHILD']['foreign_keys']
        )
    finally:
        _drop_schema_fixture(instance, schema_name)


def _execute_statement(instance: dict, query: str) -> None:
    connection = _open_connection(instance)
    try:
        cursor = ibm_db.exec_immediate(connection, query)
        ibm_db.fetch_tuple(cursor)
        ibm_db.free_result(cursor)
    finally:
        ibm_db.close(connection)


def _execute_statement_no_fetch(instance: dict, query: str) -> None:
    connection = _open_connection(instance)
    try:
        cursor = ibm_db.exec_immediate(connection, query)
        ibm_db.free_result(cursor)
    finally:
        ibm_db.close(connection)


def _drop_table_if_exists(instance: dict, table_name: str) -> None:
    try:
        _execute_statement_no_fetch(instance, f'DROP TABLE {table_name}')
    except Exception:
        pass


def _create_schema_fixture(instance: dict, schema_name: str) -> None:
    _execute_statement_no_fetch(instance, f'CREATE SCHEMA {schema_name}')
    _execute_statement_no_fetch(
        instance,
        (
            f'CREATE TABLE {schema_name}.PARENT ('
            'ID INTEGER NOT NULL, '
            'NAME VARCHAR(32), '
            'CONSTRAINT PARENT_PK PRIMARY KEY (ID)'
            ')'
        ),
    )
    _execute_statement_no_fetch(
        instance,
        (
            f'CREATE TABLE {schema_name}.CHILD ('
            'ID INTEGER NOT NULL, '
            'PARENT_ID INTEGER NOT NULL, '
            'NAME VARCHAR(32), '
            'CONSTRAINT CHILD_PK PRIMARY KEY (ID), '
            f'CONSTRAINT CHILD_PARENT_FK FOREIGN KEY (PARENT_ID) REFERENCES {schema_name}.PARENT(ID)'
            ')'
        ),
    )
    _execute_statement_no_fetch(
        instance, f'CREATE INDEX {schema_name}.CHILD_PARENT_IDX ON {schema_name}.CHILD(PARENT_ID)'
    )
    _execute_statement_no_fetch(instance, f'GRANT SELECT ON TABLE {schema_name}.PARENT TO USER {DBM_USERNAME}')
    _execute_statement_no_fetch(instance, f'GRANT SELECT ON TABLE {schema_name}.CHILD TO USER {DBM_USERNAME}')


def _drop_schema_fixture(instance: dict, schema_name: str) -> None:
    for table_name in ('CHILD', 'PARENT'):
        try:
            _execute_statement_no_fetch(instance, f'DROP TABLE {schema_name}.{table_name}')
        except Exception:
            pass
    try:
        _execute_statement_no_fetch(instance, f'DROP SCHEMA {schema_name} RESTRICT')
    except Exception:
        pass


def _open_connection(instance: dict) -> Any:
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
