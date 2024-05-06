# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import logging
from copy import copy

import pytest

from deepdiff import DeepDiff

from datadog_checks.sqlserver import SQLServer
#from deepdiff import DeepDiff - not clear how to add it to ddev

from .common import CHECK_NAME
from .utils import delete_if_found, compare_coumns_in_tables
try:
    import pyodbc
except ImportError:
    pyodbc = None
import pdb
import json

@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['min_collection_interval'] = 1
    instance_docker['query_metrics'] = {'enabled': False}
    instance_docker['query_activity'] = {'enabled': False}
    instance_docker['procedure_metrics'] = {'enabled': False}
    # set a very small collection interval so the tests go fast
    instance_docker['collect_settings'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
    }
    return copy(instance_docker)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "expected_columns,available_columns",
    [
        [
            ["name", "value"],
            ["name", "value"],
        ],
        [
            ["name", "value", "some_missing_column"],
            ["name", "value"],
        ],
    ],
)
def test_get_available_settings_columns(dbm_instance, expected_columns, available_columns):
    pass
    #check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    #check.initialize_connection()
    #_conn_key_prefix = "dbm-metadata-"
    #with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        #with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            #result_available_columns = check.sql_metadata._get_available_settings_columns(cursor, expected_columns)
            #assert result_available_columns == available_columns


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_get_settings_query_cached(dbm_instance, caplog):
    caplog.set_level(logging.DEBUG)
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-metadata"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            for _ in range(3):
                query = check.sql_metadata._get_settings_query_cached(cursor)
                assert query, "query should be non-empty"
    times_columns_loaded = 0
    for r in caplog.records:
        if r.message.startswith("found available sys.configurations columns"):
            times_columns_loaded += 1
    assert times_columns_loaded == 1, "columns should have been loaded only once"


def test_sqlserver_collect_settings(aggregator, dd_run_check, dbm_instance):
    pass
    #check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    # dd_run_check(check)
    #check.initialize_connection()
    #check.check(dbm_instance)
    #dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    #event = next((e for e in dbm_metadata if e['kind'] == 'sqlserver_configs'), None)
    #assert event is not None
    #assert event['dbms'] == "sqlserver"
    #assert event['kind'] == "sqlserver_configs"
    #assert len(event["metadata"]) > 0

#TODO this test relies on a certain granularity
#later we need to upgrade it to accumulate data for each DB before checking.
def test_collect_schemas(aggregator, dd_run_check, dbm_instance):
    
    databases_to_find  = ['datadog_test_schemas','datadog_test']
    exp_datadog_test =  {'id': '6', 'name': 'datadog_test', 'owner': 'dbo', 'schemas': [ {'name': 'dbo', 'id': '1', 'owner': '1', 'tables': [{'id': '885578193', 'name': 'ϑings', 'columns': [{'name': 'id', 'data_type': 'int', 'default': '((0))', 'nullable': True}, {'name': 'name', 'data_type': 'varchar', 'default': 'None', 'nullable': True}]}]}]}
    exp_datadog_test_schemas = {'id': '5', 'name': 'datadog_test_schemas', 'owner': 'dbo', 'schemas': [{'name': 'test_schema', 'id': '5', 'owner': '1', 'tables': [{'id': '885578193', 'name': 'cities', 'columns': [{'name': 'id', 'data_type': 'int', 'default': '((0))', 'nullable': True}, {'name': 'name', 'data_type': 'varchar', 'default': 'None', 'nullable': True}]}]}]}
    expected_data_for_db = {'datadog_test' : exp_datadog_test, 'datadog_test_schemas' : exp_datadog_test_schemas}

    dbm_instance['database_autodiscovery'] = True
    dbm_instance['autodiscovery_include'] = ['datadog_test_schemas','datadog_test']

    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)

    #extracting events.

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    
    actual_payloads = {}

    for schema_event in (e for e in dbm_metadata if e['kind'] == 'sqlserver_databases'):
        if len(databases_to_find) == 0:
            # we may see the correct payload for the database several times in events
            return

        assert schema_event.get("timestamp") is not None
        # there should only be one database, datadog_test
        
        database_metadata = schema_event['metadata']
        assert len(database_metadata) == 1
        db_name = database_metadata[0]['name']

        if db_name in actual_payloads:
            actual_payloads[db_name]['schemas'] = actual_payloads[db_name]['schemas'] + database_metadata[0]['schemas']
        else:
            actual_payloads[db_name] = database_metadata[0]
    pdb.set_trace()
    assert len(actual_payloads) == len(expected_data_for_db)    

    for db_name, actual_payload in actual_payloads.items():

        #assert delete_if_found(databases_to_find, db_name)
        assert db_name in databases_to_find
        # we need to accumulate all data ... as payloads may differ 

        difference = DeepDiff(actual_payload, expected_data_for_db[db_name], ignore_order=True)

        #difference = {}
        diff_keys = list(difference.keys())
        if len(diff_keys) > 0 and diff_keys != ['iterable_item_removed']:
            logging.debug("found the following diffs %s", json.dumps(difference))
            assert False

        # we need a special comparison as order of columns matter

        assert compare_coumns_in_tables(expected_data_for_db[db_name], actual_payload)

        print("ok")
