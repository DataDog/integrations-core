# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import logging
from copy import copy

import pytest

from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME

try:
    import pyodbc
except ImportError:
    pyodbc = None


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
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-metadata-"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            result_available_columns = check.sql_metadata._get_available_settings_columns(cursor, expected_columns)
            assert result_available_columns == available_columns


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
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    # dd_run_check(check)
    check.initialize_connection()
    check.check(dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'sqlserver_configs'), None)
    assert event is not None
    assert event['dbms'] == "sqlserver"
    assert event['kind'] == "sqlserver_configs"
    assert len(event["metadata"]) > 0
