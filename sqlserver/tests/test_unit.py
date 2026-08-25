# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import copy
import gc
import inspect
import logging
import os
import re
import weakref
from collections import namedtuple

import mock
import pytest

from datadog_checks.base.stubs.datadog_agent import datadog_agent
from datadog_checks.base.utils.db import QueryManager
from datadog_checks.dev import EnvVars
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.connection import split_sqlserver_host_port
from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_AZURE_MANAGED_INSTANCE,
    ENGINE_EDITION_SQL_DATABASE,
    ENGINE_EDITION_STANDARD,
    PERF_COUNTER_BULK_COUNT,
    STATIC_INFO_ENGINE_EDITION,
    STATIC_INFO_FULL_SERVERNAME,
    STATIC_INFO_INSTANCENAME,
    STATIC_INFO_MAJOR_VERSION,
    STATIC_INFO_RDS,
    STATIC_INFO_SERVERNAME,
    STATIC_INFO_VERSION,
)
from datadog_checks.sqlserver.database_metrics import SqlserverDatabaseStatsMetrics
from datadog_checks.sqlserver.metrics import DEFAULT_PERFORMANCE_TABLE, SqlFractionMetric, SqlSimpleMetric
from datadog_checks.sqlserver.schemas import KEY_PREFIX, KEY_PREFIX_PRE_2017, SQLServerSchemaCollector
from datadog_checks.sqlserver.sqlserver import SQLConnectionError
from datadog_checks.sqlserver.utils import (
    Database,
    construct_use_statement,
    extract_sql_comments_and_procedure_name,
    get_unixodbc_sysconfig,
    is_non_empty_file,
    needs_comment_recovery,
    parse_sqlserver_major_version,
    parse_sqlserver_year,
    set_default_driver_conf,
)

from .common import CHECK_NAME, DOCKER_SERVER, assert_metrics
from .utils import not_windows_ci, windows_ci

try:
    import pyodbc  # type: ignore
except ImportError:
    pyodbc = None

# mark the whole module
pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'db_name, expected',
    [
        ('my_database', 'USE [my_database];'),
        (']rh_bracket]', 'USE []]rh_bracket]]];'),
        ('[lh_bracket[', 'USE [[lh_bracket[];'),
        ('[bracketed]', 'USE [[bracketed]]];'),
    ],
)
def test_construct_use_statement(db_name, expected):
    """
    Test functionality of constructing USE statement
    """
    use_stmt = construct_use_statement(db_name)

    assert use_stmt == expected


@pytest.mark.parametrize('database_count', [1, 1000])
def test_autodiscovery_database_service_check_batch_count_is_bounded(instance_autodiscovery, database_count):
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    database_names = [f'database_{index}' for index in range(database_count)]
    check.databases = {Database(name) for name in database_names}
    cursor = mock.MagicMock()
    cursor.fetchall.return_value = [(name, 1) for name in database_names]
    check._connection = mock.MagicMock()
    check.connection.get_managed_cursor.return_value.__enter__.return_value = cursor
    check.handle_service_check = mock.MagicMock()

    check._check_connections_by_use_db()

    cursor.execute.assert_called_once()
    query, params = cursor.execute.call_args.args
    assert query.count('?') == 1
    assert 'USE ' not in query
    assert params[0].count('<database>') == database_count
    assert check.handle_service_check.call_count == database_count


def test_autodiscovery_database_service_check_preserves_per_database_status(instance_autodiscovery):
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.databases = {Database('available'), Database('unavailable')}
    cursor = mock.MagicMock()
    cursor.fetchall.return_value = [('available', 1), ('unavailable', 0)]
    check._connection = mock.MagicMock()
    check.connection.get_managed_cursor.return_value.__enter__.return_value = cursor
    check.connection.get_host_with_port = mock.MagicMock(return_value='sql.example:1433')
    check.handle_service_check = mock.MagicMock()

    check._check_connections_by_use_db()

    check.handle_service_check.assert_has_calls(
        [
            mock.call(check.OK, 'sql.example:1433', 'available', False),
            mock.call(
                check.CRITICAL,
                'sql.example:1433',
                'unavailable',
                'Database unavailable connection service check failed: database is not accessible',
                False,
            ),
        ],
        any_order=True,
    )


def test_execute_query_raw_collects_multiple_result_sets(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    cursor = mock.MagicMock()
    cursor.description = [('value',)]
    cursor.fetchall.side_effect = [[('first',)], [('second',)]]
    cursor.nextset.side_effect = [True, False]
    check._connection = mock.MagicMock()
    check.connection.get_managed_cursor.return_value.__enter__.return_value = cursor

    rows = check.execute_query_raw('SELECT 1; SELECT 2', fetch_multiple_results=True)

    assert rows == [('first',), ('second',)]
    assert cursor.fetchall.call_count == 2


def create_schema_collector(static_info_cache: dict | None = None) -> SQLServerSchemaCollector:
    check = mock.Mock()
    check._config.schema_config = {}
    check.log = mock.Mock()
    check.static_info_cache = static_info_cache or {}
    return SQLServerSchemaCollector(check)


def test_schema_collector_records_database_compatibility_levels() -> None:
    collector = create_schema_collector({})
    databases = [
        {
            "name": "db_130",
            "id": "1",
            "collation": "SQL_Latin1_General_CP1_CI_AS",
            "owner": "dbo",
            "compatibility_level": "130",
        },
        {
            "name": "db_120",
            "id": "2",
            "collation": "SQL_Latin1_General_CP1_CI_AS",
            "owner": "dbo",
            "compatibility_level": "120",
        },
    ]

    collector._record_database_compatibility_levels(databases)

    assert collector._database_compatibility_levels == {"db_130": 130, "db_120": 120}
    assert databases == [
        {
            "name": "db_130",
            "id": "1",
            "collation": "SQL_Latin1_General_CP1_CI_AS",
            "owner": "dbo",
            "compatibility_level": "130",
        },
        {
            "name": "db_120",
            "id": "2",
            "collation": "SQL_Latin1_General_CP1_CI_AS",
            "owner": "dbo",
            "compatibility_level": "120",
        },
    ]


def test_schema_collector_emits_database_compatibility_levels() -> None:
    collector = create_schema_collector({})
    collector._check.get_databases.return_value = ["db_130"]
    cursor = mock.Mock()
    collector._check.connection.open_managed_default_connection.return_value = contextlib.nullcontext()
    collector._check.connection.get_managed_cursor.return_value = contextlib.nullcontext(cursor)
    databases = [
        {
            "name": "db_130",
            "id": "1",
            "collation": "SQL_Latin1_General_CP1_CI_AS",
            "owner": "dbo",
            "compatibility_level": "130",
        }
    ]

    with mock.patch("datadog_checks.sqlserver.schemas.execute_query", return_value=databases):
        collected_databases = collector._get_databases()

    assert collector._database_compatibility_levels == {"db_130": 130}
    assert collected_databases == [
        {
            "name": "db_130",
            "id": "1",
            "collation": "SQL_Latin1_General_CP1_CI_AS",
            "owner": "dbo",
            "compatibility_level": "130",
        }
    ]
    assert databases[0]["compatibility_level"] == "130"


@pytest.mark.parametrize(
    'engine_edition, major_version, compatibility_level, expected_legacy',
    [
        (ENGINE_EDITION_SQL_DATABASE, 12, 130, False),
        (ENGINE_EDITION_SQL_DATABASE, 12, 120, True),
        (ENGINE_EDITION_AZURE_MANAGED_INSTANCE, 12, 130, False),
        (ENGINE_EDITION_AZURE_MANAGED_INSTANCE, 12, 120, True),
        (ENGINE_EDITION_STANDARD, 13, 170, True),
        (ENGINE_EDITION_STANDARD, 14, 130, False),
        (ENGINE_EDITION_STANDARD, 14, 100, True),
        (ENGINE_EDITION_STANDARD, 0, 170, True),
    ],
)
def test_schema_collector_legacy_query_detection(
    engine_edition: int, major_version: int, compatibility_level: int, expected_legacy: bool
) -> None:
    collector = create_schema_collector(
        {
            STATIC_INFO_ENGINE_EDITION: engine_edition,
            STATIC_INFO_MAJOR_VERSION: major_version,
        }
    )
    collector._database_compatibility_levels = {"datadog_test": compatibility_level}

    assert collector._should_use_legacy_schema_query("datadog_test") is expected_legacy


@pytest.mark.parametrize(
    'engine_edition, major_version',
    [
        (ENGINE_EDITION_SQL_DATABASE, 12),
        (ENGINE_EDITION_AZURE_MANAGED_INSTANCE, 12),
        (ENGINE_EDITION_STANDARD, 14),
    ],
)
def test_schema_collector_uses_legacy_query_when_compatibility_level_is_not_recorded(
    engine_edition: int, major_version: int
) -> None:
    collector = create_schema_collector(
        {
            STATIC_INFO_ENGINE_EDITION: engine_edition,
            STATIC_INFO_MAJOR_VERSION: major_version,
        }
    )

    assert collector._should_use_legacy_schema_query("datadog_test") is True


@pytest.mark.parametrize(
    'engine_edition, major_version, compatibility_level, expected_legacy',
    [
        (ENGINE_EDITION_SQL_DATABASE, 12, 130, False),
        (ENGINE_EDITION_SQL_DATABASE, 12, 120, True),
        (ENGINE_EDITION_AZURE_MANAGED_INSTANCE, 12, 130, False),
        (ENGINE_EDITION_AZURE_MANAGED_INSTANCE, 12, 120, True),
        (ENGINE_EDITION_STANDARD, 14, 130, False),
        (ENGINE_EDITION_STANDARD, 14, 120, True),
    ],
)
def test_schema_collector_uses_database_compatibility_level_for_schema_query(
    engine_edition: int, major_version: int, compatibility_level: int, expected_legacy: bool
) -> None:
    collector = create_schema_collector(
        {
            STATIC_INFO_ENGINE_EDITION: engine_edition,
            STATIC_INFO_MAJOR_VERSION: major_version,
        }
    )
    collector._database_compatibility_levels = {"datadog_test": compatibility_level}
    main_cursor = mock.Mock()
    detail_cursor = mock.Mock()
    collector._check.connection.open_managed_default_connection.side_effect = [
        contextlib.nullcontext(),
        contextlib.nullcontext(),
    ]
    collector._check.connection.get_managed_cursor.side_effect = [
        contextlib.nullcontext(main_cursor),
        contextlib.nullcontext(detail_cursor),
    ]

    with collector._get_cursor("datadog_test"):
        pass

    tables_query = main_cursor.execute.call_args_list[1][0][0]
    assert collector._is_2016_or_earlier is expected_legacy
    assert ("STRING_AGG" in tables_query) is not expected_legacy
    assert (detail_cursor.execute.call_count == 1) is expected_legacy


def test_schema_collector_reuses_pre_2017_connection_for_table_detail_queries() -> None:
    collector = create_schema_collector(
        {
            STATIC_INFO_ENGINE_EDITION: ENGINE_EDITION_STANDARD,
            STATIC_INFO_MAJOR_VERSION: 13,
        }
    )
    main_cursor = mock.Mock()
    detail_cursor = mock.Mock()
    detail_cursor.fetchall_dict.side_effect = [
        [{"name": "id"}],
        [{"name": "pk_table_1"}],
        [{"foreign_key_name": "fk_table_1"}],
        [{"name": "id"}],
        [{"name": "pk_table_2"}],
        [{"foreign_key_name": "fk_table_2"}],
    ]
    detail_cursor.fetchone_dict.side_effect = [{"partition_count": 1}, {"partition_count": 2}]
    collector._check.connection.open_managed_default_connection.side_effect = [
        contextlib.nullcontext(),
        contextlib.nullcontext(),
    ]
    collector._check.connection.get_managed_cursor.side_effect = [
        contextlib.nullcontext(main_cursor),
        contextlib.nullcontext(detail_cursor),
    ]
    database = {"name": "datadog_test", "id": "1", "collation": "SQL_Latin1_General_CP1_CI_AS", "owner": "dbo"}
    rows = [
        {"schema_name": "test_schema", "schema_id": 1, "owner_name": "dbo", "table_name": "table_1", "table_id": 101},
        {"schema_name": "test_schema", "schema_id": 1, "owner_name": "dbo", "table_name": "table_2", "table_id": 102},
    ]

    with collector._get_cursor("datadog_test"):
        mapped_rows = [collector._map_row(database, row) for row in rows]

    assert collector._check.connection.open_managed_default_connection.call_args_list == [
        mock.call(KEY_PREFIX),
        mock.call(KEY_PREFIX_PRE_2017),
    ]
    assert collector._check.connection.get_managed_cursor.call_args_list == [
        mock.call(KEY_PREFIX),
        mock.call(KEY_PREFIX_PRE_2017),
    ]
    assert detail_cursor.execute.call_args_list[0] == mock.call("USE [datadog_test];")
    assert detail_cursor.execute.call_args_list.count(mock.call("USE [datadog_test];")) == 1
    assert detail_cursor.execute.call_count == 9
    assert collector._pre_2017_cursor is None
    assert [row["schemas"][0]["tables"][0]["partitions"]["partition_count"] for row in mapped_rows] == [1, 2]


def configure_pre_2017_detail_cursor(cursor: mock.Mock, partition_count: int = 1) -> None:
    cursor.fetchall_dict.side_effect = [
        [{"name": "id"}],
        [{"name": "pk_table"}],
        [{"foreign_key_name": "fk_table"}],
    ]
    cursor.fetchone_dict.return_value = {"partition_count": partition_count}


def test_schema_collector_uses_new_pre_2017_connection_for_each_database() -> None:
    collector = create_schema_collector(
        {
            STATIC_INFO_ENGINE_EDITION: ENGINE_EDITION_STANDARD,
            STATIC_INFO_MAJOR_VERSION: 13,
        }
    )
    main_cursor_1 = mock.Mock()
    detail_cursor_1 = mock.Mock()
    configure_pre_2017_detail_cursor(detail_cursor_1, partition_count=1)
    main_cursor_2 = mock.Mock()
    detail_cursor_2 = mock.Mock()
    configure_pre_2017_detail_cursor(detail_cursor_2, partition_count=2)
    collector._check.connection.open_managed_default_connection.side_effect = [
        contextlib.nullcontext(),
        contextlib.nullcontext(),
        contextlib.nullcontext(),
        contextlib.nullcontext(),
    ]
    collector._check.connection.get_managed_cursor.side_effect = [
        contextlib.nullcontext(main_cursor_1),
        contextlib.nullcontext(detail_cursor_1),
        contextlib.nullcontext(main_cursor_2),
        contextlib.nullcontext(detail_cursor_2),
    ]
    row = {"schema_name": "test_schema", "schema_id": 1, "owner_name": "dbo", "table_name": "table", "table_id": 101}

    with collector._get_cursor("datadog_test_1"):
        collector._map_row(
            {"name": "datadog_test_1", "id": "1", "collation": "SQL_Latin1_General_CP1_CI_AS", "owner": "dbo"},
            row,
        )
    with collector._get_cursor("datadog_test_2"):
        collector._map_row(
            {"name": "datadog_test_2", "id": "2", "collation": "SQL_Latin1_General_CP1_CI_AS", "owner": "dbo"},
            row,
        )

    assert collector._check.connection.get_managed_cursor.call_args_list == [
        mock.call(KEY_PREFIX),
        mock.call(KEY_PREFIX_PRE_2017),
        mock.call(KEY_PREFIX),
        mock.call(KEY_PREFIX_PRE_2017),
    ]
    assert detail_cursor_1.execute.call_args_list[0] == mock.call("USE [datadog_test_1];")
    assert detail_cursor_2.execute.call_args_list[0] == mock.call("USE [datadog_test_2];")
    assert collector._pre_2017_cursor is None


def test_schema_collector_does_not_open_pre_2017_connection_for_modern_query() -> None:
    collector = create_schema_collector(
        {
            STATIC_INFO_ENGINE_EDITION: ENGINE_EDITION_STANDARD,
            STATIC_INFO_MAJOR_VERSION: 14,
        }
    )
    collector._database_compatibility_levels = {"datadog_test": 130}
    cursor = mock.Mock()
    collector._check.connection.open_managed_default_connection.return_value = contextlib.nullcontext()
    collector._check.connection.get_managed_cursor.return_value = contextlib.nullcontext(cursor)
    database = {"name": "datadog_test", "id": "1", "collation": "SQL_Latin1_General_CP1_CI_AS", "owner": "dbo"}
    row = {
        "schema_name": "test_schema",
        "schema_id": 1,
        "owner_name": "dbo",
        "table_name": "table",
        "table_id": 101,
        "columns": '[{"name": "id"}]',
        "indexes": '[{"name": "pk_table"}]',
        "foreign_keys": '[{"foreign_key_name": "fk_table"}]',
        "partition_count": 1,
    }

    with collector._get_cursor("datadog_test"):
        mapped_row = collector._map_row(database, row)

    assert collector._check.connection.open_managed_default_connection.call_args_list == [mock.call(KEY_PREFIX)]
    assert collector._check.connection.get_managed_cursor.call_args_list == [mock.call(KEY_PREFIX)]
    assert collector._pre_2017_cursor is None
    assert mapped_row["schemas"][0]["tables"][0]["columns"] == [{"name": "id"}]


def test_get_cursor(instance_docker):
    """
    Ensure we don't leak connection info in case of a KeyError when the
    connection pool is empty or the params for `get_cursor` are invalid.
    """
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()
    with pytest.raises(SQLConnectionError):
        check.connection.get_cursor('foo')


def test_stored_procedure_check_closes_connection_on_error(instance_docker):
    instance = copy.copy(instance_docker)
    instance['stored_procedure'] = 'fake_proc'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()

    mock_cursor = mock.MagicMock()
    mock_cursor.execute.side_effect = Exception("proc failed")
    mock_cursor.callproc.side_effect = Exception("proc failed")

    with (
        mock.patch.object(check.connection, 'open_db_connections') as open_db,
        mock.patch.object(check.connection, 'close_db_connections') as close_db,
        mock.patch.object(check.connection, 'get_cursor', return_value=mock_cursor),
        mock.patch.object(check.connection, 'close_cursor') as close_cursor,
    ):
        with pytest.raises(Exception, match="proc failed"):
            check.do_stored_procedure_check()

    open_db.assert_called_once()
    close_db.assert_called_once()
    close_cursor.assert_called_once_with(mock_cursor)


def test_missing_db(instance_docker, dd_run_check):
    instance = copy.copy(instance_docker)
    instance['ignore_missing_database'] = False

    with mock.patch(
        'datadog_checks.sqlserver.connection.Connection.open_managed_default_connection',
        side_effect=SQLConnectionError(Exception("couldnt connect")),
    ):
        with pytest.raises(SQLConnectionError):
            check = SQLServer(CHECK_NAME, {}, [instance])
            check.initialize_connection()
            check.make_metric_list_to_collect()

    instance['ignore_missing_database'] = True
    with mock.patch('datadog_checks.sqlserver.connection.Connection.check_database', return_value=(False, 'db')):
        check = SQLServer(CHECK_NAME, {}, [instance])
        # Saturate static information to avoid trying to connect to the database
        expected_keys = {
            STATIC_INFO_VERSION,
            STATIC_INFO_MAJOR_VERSION,
            STATIC_INFO_ENGINE_EDITION,
            STATIC_INFO_RDS,
            STATIC_INFO_SERVERNAME,
            STATIC_INFO_INSTANCENAME,
        }
        for key in expected_keys:
            check.static_info_cache[key] = 'foo'

        check.initialize_connection()
        check.make_metric_list_to_collect()
        dd_run_check(check)
        assert check.do_check is False


@mock.patch('datadog_checks.sqlserver.connection.Connection.open_managed_default_database')
@mock.patch('datadog_checks.sqlserver.connection.Connection.get_cursor')
def test_db_exists(get_cursor, mock_connect, instance_docker_defaults, dd_run_check):
    Row = namedtuple('Row', 'name,collation_name')
    db_results = [
        Row('master', 'SQL_Latin1_General_CP1_CI_AS'),
        Row('tempdb', 'SQL_Latin1_General_CP1_CI_AS'),
        Row('AdventureWorks2017', 'SQL_Latin1_General_CP1_CI_AS'),
        Row('CaseSensitive2018', 'SQL_Latin1_General_CP1_CS_AS'),
        Row('OfflineDB', None),
    ]

    mock_connect.__enter__ = mock.Mock(return_value='foo')

    mock_results = mock.MagicMock()
    mock_results.fetchall.return_value = db_results
    get_cursor.return_value = mock_results

    instance = copy.copy(instance_docker_defaults)
    # make sure check doesn't try to add metrics
    instance['stored_procedure'] = 'fake_proc'
    instance['ignore_missing_database'] = True

    # check base case of lowercase for lowercase and case-insensitive db
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    check.make_metric_list_to_collect()
    assert check.do_check is True
    # check all caps for case insensitive db
    instance['database'] = 'MASTER'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    check.make_metric_list_to_collect()
    assert check.do_check is True

    # check mixed case against mixed case but case-insensitive db
    instance['database'] = 'AdventureWORKS2017'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    check.make_metric_list_to_collect()
    assert check.do_check is True

    # check case sensitive but matched db
    instance['database'] = 'CaseSensitive2018'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    check.make_metric_list_to_collect()
    assert check.do_check is True

    # check case sensitive but mismatched db
    instance['database'] = 'cASEsENSITIVE2018'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    check.make_metric_list_to_collect()
    assert check.do_check is False

    # check offline but exists db
    instance['database'] = 'Offlinedb'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    check.make_metric_list_to_collect()
    assert check.do_check is True


@mock.patch('datadog_checks.sqlserver.connection.Connection.open_managed_default_database')
@mock.patch('datadog_checks.sqlserver.connection.Connection.get_cursor')
def test_azure_cross_database_queries_excluded(get_cursor, mock_connect, instance_docker_defaults, dd_run_check):
    Row = namedtuple('Row', 'name,collation_name')
    db_results = [
        Row('master', 'SQL_Latin1_General_CP1_CI_AS'),
        Row('tempdb', 'SQL_Latin1_General_CP1_CI_AS'),
        Row('AdventureWorks2017', 'SQL_Latin1_General_CP1_CI_AS'),
        Row('CaseSensitive2018', 'SQL_Latin1_General_CP1_CS_AS'),
        Row('OfflineDB', None),
    ]

    mock_connect.__enter__ = mock.Mock(return_value='foo')

    mock_results = mock.MagicMock()
    mock_results.fetchall.return_value = db_results
    get_cursor.return_value = mock_results

    instance = copy.copy(instance_docker_defaults)
    instance['stored_procedure'] = 'fake_proc'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    check.make_metric_list_to_collect()
    cross_database_metrics = [
        metric
        for metric in check.instance_metrics
        if metric.__class__.TABLE not in ['msdb.dbo.backupset', 'sys.dm_db_file_space_usage']
    ]
    assert len(cross_database_metrics) == 0


def _statement_metrics_check(instance, engine_edition, disable_secondary_tags):
    instance = copy.deepcopy(instance)
    instance['dbm'] = True
    instance['query_metrics'] = {'disable_secondary_tags': disable_secondary_tags}
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.static_info_cache[STATIC_INFO_ENGINE_EDITION] = engine_edition
    return check


def _mock_query_stats_cursor():
    cursor = mock.MagicMock()
    cursor.description = [('execution_count',), ('total_elapsed_time',), ('total_worker_time',)]
    return cursor


@pytest.mark.parametrize(
    'engine_edition, disable_secondary_tags, expect_db_name_func, expect_database_name, expect_plan_attributes',
    [
        pytest.param(ENGINE_EDITION_SQL_DATABASE, True, True, True, False, id='azure_sql_database_no_secondary_tags'),
        pytest.param(ENGINE_EDITION_SQL_DATABASE, False, False, True, True, id='azure_sql_database_default'),
        # Managed Instance is an Azure engine but is not scoped to one database, so it is excluded like self-hosted.
        pytest.param(ENGINE_EDITION_STANDARD, True, False, False, False, id='self_hosted_no_secondary_tags'),
        pytest.param(ENGINE_EDITION_STANDARD, False, False, True, True, id='self_hosted_default'),
        pytest.param(
            ENGINE_EDITION_AZURE_MANAGED_INSTANCE,
            True,
            False,
            False,
            False,
            id='azure_managed_instance_no_secondary_tags',
        ),
        pytest.param(
            ENGINE_EDITION_AZURE_MANAGED_INSTANCE, False, False, True, True, id='azure_managed_instance_default'
        ),
    ],
)
def test_statement_metrics_query_database_name_column(
    instance_docker,
    engine_edition,
    disable_secondary_tags,
    expect_db_name_func,
    expect_database_name,
    expect_plan_attributes,
):
    check = _statement_metrics_check(instance_docker, engine_edition, disable_secondary_tags)
    query = check.statement_metrics._get_statement_metrics_query_cached(_mock_query_stats_cursor())

    assert ('DB_NAME() as database_name' in query) == expect_db_name_func
    assert ('as database_name' in query) == expect_database_name
    assert ('sys.dm_exec_plan_attributes' in query) == expect_plan_attributes


@pytest.mark.parametrize(
    'configured_database, row_database_name, expected',
    [
        pytest.param('mydb', 'mydb', True, id='row_matches_configured_database'),
        pytest.param('mydb', 'MyDb', True, id='row_matches_case_insensitively'),
        pytest.param('mydb', 'otherdb', False, id='row_from_another_database_excluded'),
        pytest.param('master', 'mydb', True, id='master_includes_all_rows'),
        pytest.param(None, 'mydb', True, id='no_configured_database_includes_all_rows'),
    ],
)
def test_azure_sql_database_row_filtering_with_secondary_tags_disabled(
    instance_docker, configured_database, row_database_name, expected
):
    # Supplying database_name makes the Azure SQL Database row filter reachable under this setting for the first time.
    instance = copy.deepcopy(instance_docker)
    if configured_database is None:
        instance.pop('database', None)
    else:
        instance['database'] = configured_database
    check = _statement_metrics_check(instance, ENGINE_EDITION_SQL_DATABASE, True)

    row = {'database_name': row_database_name, 'execution_count': 1}
    assert check.statement_metrics._should_include_query_metrics_row(row) is expected


def test_autodiscovery_matches_all_by_default(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list()
    all_dbs = {Database(r.name) for r in fetchall_results}
    # check base case of default filters
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    assert check.databases == all_dbs


def test_azure_autodiscovery_matches_all_by_default(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list_azure()
    all_dbs = {Database(r.name, r.physical_database_name) for r in fetchall_results}

    # check base case of default filters
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    assert check.databases == all_dbs


def test_autodiscovery_matches_none(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list()
    # check missing additions, but no exclusions
    mock_cursor.fetchall.return_value = iter(fetchall_results)  # reset the mock results
    instance_autodiscovery['autodiscovery_include'] = ['missingdb', 'fakedb']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    assert check.databases == set()


def test_azure_autodiscovery_matches_none(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list_azure()
    # check missing additions, but no exclusions
    mock_cursor.fetchall.return_value = iter(fetchall_results)  # reset the mock results
    instance_autodiscovery['autodiscovery_include'] = ['missingdb', 'fakedb']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    assert check.databases == set()


def test_autodiscovery_matches_some(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list()
    instance_autodiscovery['autodiscovery_include'] = ['master', 'fancy2020db', 'missingdb', 'fakedb']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    dbs = [Database(name) for name in ['master', 'Fancy2020db']]
    assert check.databases == set(dbs)


def test_azure_autodiscovery_matches_some(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list_azure()
    instance_autodiscovery['autodiscovery_include'] = ['master', 'fancy2020db', 'missingdb', 'fakedb']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    dbs = [Database(name, pys_db) for name, pys_db in {'master': 'master', 'Fancy2020db': '40e688a7e268'}.items()]
    assert check.databases == set(dbs)


def test_autodiscovery_exclude_some(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list()
    instance_autodiscovery['autodiscovery_include'] = ['.*']  # replace default `.*`
    instance_autodiscovery['autodiscovery_exclude'] = ['.*2020db$', 'm.*']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    dbs = [Database(name) for name in ['tempdb', 'AdventureWorks2017', 'CaseSensitive2018']]
    assert check.databases == set(dbs)


def test_azure_autodiscovery_exclude_some(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list_azure()
    instance_autodiscovery['autodiscovery_include'] = ['.*']  # replace default `.*`
    instance_autodiscovery['autodiscovery_exclude'] = ['.*2020db$', 'm.*']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    db_dict = {'tempdb': 'tempdb', 'AdventureWorks2017': 'fce04774', 'CaseSensitive2018': 'jub3j8kh'}
    dbs = [Database(name, pys_db) for name, pys_db in db_dict.items()]
    assert check.databases == set(dbs)


def test_autodiscovery_exclude_override(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list()
    instance_autodiscovery['autodiscovery_include'] = ['t.*', 'master']  # remove default `.*`
    instance_autodiscovery['autodiscovery_exclude'] = ['.*2020db$', 'm.*']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    assert check.databases == {Database("tempdb")}


def test_azure_autodiscovery_exclude_override(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list_azure()
    instance_autodiscovery['autodiscovery_include'] = ['t.*', 'master']  # remove default `.*`
    instance_autodiscovery['autodiscovery_exclude'] = ['.*2020db$', 'm.*']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    assert check.databases == {Database("tempdb", "tempdb")}


def test_autodiscovery_resets_database_metrics_on_db_removal(instance_autodiscovery):
    """When autodiscovery detects databases were removed, _database_metrics must be
    reset so that query executors are rebuilt without the deleted databases."""
    fetchall_results, mock_cursor = _mock_database_list()
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])

    # First autodiscovery run — discovers all databases
    check.autodiscover_databases(mock_cursor)
    assert check.databases == {Database(r.name) for r in fetchall_results}

    # Simulate _database_metrics being built (as happens during collect_metrics)
    check._database_metrics = [mock.MagicMock()]
    assert check._database_metrics is not None

    # Second autodiscovery run with a database removed — simulate by returning fewer rows
    Row = namedtuple('Row', 'name')
    reduced_results = [Row('master'), Row('tempdb'), Row('msdb')]
    mock_cursor.fetchall.return_value = iter(reduced_results)
    check._ad_last_check = 0  # force autodiscovery to run again

    changed = check.autodiscover_databases(mock_cursor)
    assert changed is True
    assert check.databases == {Database('master'), Database('tempdb'), Database('msdb')}
    assert check._database_metrics is None


def test_autodiscovery_resets_database_metrics_on_db_addition(instance_autodiscovery):
    """When autodiscovery detects new databases were added, _database_metrics must be
    reset so that query executors are rebuilt to include the new databases."""
    Row = namedtuple('Row', 'name')
    initial_results = [Row('master'), Row('tempdb')]
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = iter(initial_results)

    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])

    # First autodiscovery run
    check.autodiscover_databases(mock_cursor)
    assert check.databases == {Database('master'), Database('tempdb')}

    # Simulate _database_metrics being built
    check._database_metrics = [mock.MagicMock()]

    # Second autodiscovery run with a database added
    expanded_results = [Row('master'), Row('tempdb'), Row('newdb')]
    mock_cursor.fetchall.return_value = iter(expanded_results)
    check._ad_last_check = 0

    changed = check.autodiscover_databases(mock_cursor)
    assert changed is True
    assert check.databases == {Database('master'), Database('tempdb'), Database('newdb')}
    assert check._database_metrics is None


def test_autodiscovery_resets_database_metrics_after_initial_empty_result(instance_autodiscovery):
    """Database metric executors must refresh when an initially empty discovery later finds a database."""
    _, mock_cursor = _mock_database_list()
    instance_autodiscovery['autodiscovery_include'] = ['newdb$']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])

    changed = check.autodiscover_databases(mock_cursor)
    assert changed is False
    assert check.databases == set()

    assert check.database_metrics

    Row = namedtuple('Row', 'name')
    mock_cursor.fetchall.return_value = iter([Row('newdb')])
    check._ad_last_check = 0

    changed = check.autodiscover_databases(mock_cursor)
    assert changed is True
    assert check.databases == {Database('newdb')}
    database_stats_metrics = next(
        metric for metric in check.database_metrics if isinstance(metric, SqlserverDatabaseStatsMetrics)
    )
    assert [query.get('params') for query in database_stats_metrics.queries] == [('newdb',)]


@pytest.mark.parametrize(
    'base_name',
    [
        pytest.param('Buffer cache hit ratio base', id='base_name valid'),
        pytest.param(None, id='base_name None'),
    ],
)
def test_SqlFractionMetric_base(caplog, base_name):
    fetchall_results = [
        _padded_counter_row('Buffer cache hit ratio', '', 'SQLServer:Buffer Manager', 33453),
        _padded_counter_row('Buffer cache hit ratio base', '', 'SQLServer:Buffer Manager', 33531),
        _padded_counter_row('some random counter', '', 'SQLServer:Buffer Manager', 1111),
        _padded_counter_row('some random counter base', '', 'SQLServer:Buffer Manager', 33531),
    ]
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = fetchall_results

    report_function = mock.MagicMock()
    metric_obj = SqlFractionMetric(
        cfg_instance={
            'name': 'sqlserver.buffer.cache_hit_ratio',
            'counter_name': 'Buffer cache hit ratio',
            'instance_name': '',
            'physical_db_name': None,
            'tags': ['optional:tag1', 'dd.internal.resource:database_instance:stubbed.hostname'],
            'hostname': 'stubbed.hostname',
        },
        base_name=base_name,
        report_function=report_function,
        column=None,
        logger=mock.MagicMock(),
    )
    results_rows, results_cols = SqlFractionMetric.fetch_all_values(
        mock_cursor, ['Buffer cache hit ratio', base_name], mock.mock.MagicMock()
    )
    metric_obj.fetch_metric(results_rows, results_cols)
    if base_name:
        report_function.assert_called_with(
            'sqlserver.buffer.cache_hit_ratio',
            0.9976737943992127,
            raw=True,
            hostname='stubbed.hostname',
            tags=['optional:tag1', 'dd.internal.resource:database_instance:stubbed.hostname'],
        )
    else:
        report_function.assert_not_called()


def test_SqlFractionMetric_group_by_instance(caplog):
    fetchall_results = [
        _padded_counter_row('Buffer cache hit ratio', '', 'SQLServer:Buffer Manager', 33453),
        _padded_counter_row('Buffer cache hit ratio base', '', 'SQLServer:Buffer Manager', 33531),
        _padded_counter_row('Foo counter', 'bar', 'SQLServer:Buffer Manager', 1),
        _padded_counter_row('Foo counter base', 'bar', 'SQLServer:Buffer Manager', 50),
        _padded_counter_row('Foo counter', 'zoo', 'SQLServer:Buffer Manager', 5),
        _padded_counter_row('Foo counter base', 'zoo', 'SQLServer:Buffer Manager', 100),
    ]
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = fetchall_results

    report_function = mock.MagicMock()
    metric_obj = SqlFractionMetric(
        cfg_instance={
            'name': 'sqlserver.test.metric',
            'counter_name': 'Foo counter',
            'instance_name': 'ALL',
            'physical_db_name': None,
            'tags': ['optional:tag1', 'dd.internal.resource:database_instance:stubbed.hostname'],
            'hostname': 'stubbed.hostname',
            'tag_by': 'db',
        },
        base_name='Foo counter base',
        report_function=report_function,
        column=None,
        logger=mock.MagicMock(),
    )
    results_rows, results_cols = SqlFractionMetric.fetch_all_values(
        mock_cursor, ['Foo counter base', 'Foo counter'], mock.mock.MagicMock()
    )
    metric_obj.fetch_metric(results_rows, results_cols)
    report_function.assert_any_call(
        'sqlserver.test.metric',
        0.02,
        raw=True,
        hostname='stubbed.hostname',
        tags=['optional:tag1', 'dd.internal.resource:database_instance:stubbed.hostname', 'db:bar'],
    )
    report_function.assert_any_call(
        'sqlserver.test.metric',
        0.05,
        raw=True,
        hostname='stubbed.hostname',
        tags=['optional:tag1', 'dd.internal.resource:database_instance:stubbed.hostname', 'db:zoo'],
    )


# sys.dm_os_performance_counters declares the name columns as nchar(128), so every value comes back
# blank-padded. Pad the fixtures the same way to exercise the stripping.
def _padded_counter_row(
    counter_name: str,
    instance_name: str,
    object_name: str,
    cntr_value: int,
) -> tuple[str, str, str, int]:
    return (counter_name.ljust(128), instance_name.ljust(128), object_name.ljust(128), cntr_value)


def test_SqlFractionMetric_skips_instances_without_a_base_counter():
    """An instance whose base counter is missing must be skipped, and the others still reported.

    A base counter recorded for one instance says nothing about another, and dividing by it would report a
    wrong value for every instance that has no base of its own.
    """
    fetchall_results = [
        _padded_counter_row('Foo counter', 'bar', 'SQLServer:Buffer Manager', 1),
        _padded_counter_row('Foo counter', 'zoo', 'SQLServer:Buffer Manager', 5),
        _padded_counter_row('Foo counter base', 'zoo', 'SQLServer:Buffer Manager', 100),
    ]
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = fetchall_results

    report_function = mock.MagicMock()
    metric_obj = SqlFractionMetric(
        cfg_instance={
            'name': 'sqlserver.test.metric',
            'counter_name': 'Foo counter',
            'instance_name': 'ALL',
            'physical_db_name': None,
            'tags': ['optional:tag1'],
            'hostname': 'stubbed.hostname',
            'tag_by': 'db',
        },
        base_name='Foo counter base',
        report_function=report_function,
        column=None,
        logger=mock.MagicMock(),
    )
    results, columns = SqlFractionMetric.fetch_all_values(
        mock_cursor, ['Foo counter', 'Foo counter base'], mock.MagicMock()
    )
    metric_obj.fetch_metric(results, columns)

    assert report_function.call_args_list == [
        mock.call(
            'sqlserver.test.metric', 0.05, raw=True, hostname='stubbed.hostname', tags=['optional:tag1', 'db:zoo']
        )
    ]


SIMPLE_METRIC_ROWS = [
    _padded_counter_row('Processes blocked', '', 'SQLServer:General Statistics', 1),
    _padded_counter_row('Cache Pages', '_Total', 'SQLServer:Plan Cache', 10),
    _padded_counter_row('Cache Pages', 'SQL Plans', 'SQLServer:Plan Cache', 11),
    _padded_counter_row('Cache Pages', 'Object Plans', 'SQLServer:Plan Cache', 12),
    _padded_counter_row('Transaction Delay', 'tenant_a', 'SQLServer:Database Replica', 20),
    _padded_counter_row('Transaction Delay', 'tenant_a', 'SQLServer:Databases', 21),
    _padded_counter_row('Log Flushes/sec', '_Total', 'SQLServer:Databases', 30),
    _padded_counter_row('Log Flushes/sec', 'tenant_a', 'SQLServer:Databases', 31),
    _padded_counter_row('Log Flushes/sec', 'physical_a', 'SQLServer:Databases', 32),
]

SIMPLE_METRIC_TAGS = ['optional:tag1', 'dd.internal.resource:database_instance:stubbed.hostname']


@pytest.mark.parametrize(
    'cfg_overrides, expected',
    [
        pytest.param(
            {'counter_name': 'Processes blocked', 'instance_name': ''},
            [(1, SIMPLE_METRIC_TAGS)],
            id='instance level counter',
        ),
        pytest.param(
            {'counter_name': 'Log Flushes/sec', 'instance_name': '_Total'},
            [(30, SIMPLE_METRIC_TAGS)],
            id='total instance of a per database counter',
        ),
        pytest.param(
            {'counter_name': 'Log Flushes/sec', 'instance_name': 'tenant_a'},
            [(31, SIMPLE_METRIC_TAGS)],
            id='per database counter matched by instance_name',
        ),
        pytest.param(
            {'counter_name': 'Log Flushes/sec', 'instance_name': 'tenant_b', 'physical_db_name': 'physical_a'},
            [(32, SIMPLE_METRIC_TAGS)],
            id='per database counter matched by physical_db_name',
        ),
        pytest.param(
            {
                'counter_name': 'Transaction Delay',
                'instance_name': 'tenant_a',
                'object_name': 'SQLServer:Databases',
            },
            [(21, SIMPLE_METRIC_TAGS)],
            id='object_name selects among counters sharing a name',
        ),
        pytest.param(
            {'counter_name': 'Transaction Delay', 'instance_name': 'tenant_a', 'object_name': 'SQLServer:Missing'},
            [],
            id='object_name matching nothing submits nothing',
        ),
        pytest.param(
            {'counter_name': 'Cache Pages', 'instance_name': 'ALL', 'tag_by': 'plan_type'},
            [(11, SIMPLE_METRIC_TAGS + ['plan_type:SQL Plans']), (12, SIMPLE_METRIC_TAGS + ['plan_type:Object Plans'])],
            id='ALL instances tags each instance and skips _Total',
        ),
        pytest.param(
            {
                'counter_name': 'Transaction Delay',
                'instance_name': 'ALL',
                'tag_by': 'db',
                'object_name': 'SQLServer:Missing',
            },
            [(20, SIMPLE_METRIC_TAGS + ['db:tenant_a']), (21, SIMPLE_METRIC_TAGS + ['db:tenant_a'])],
            id='ALL instances ignores object_name',
        ),
        pytest.param(
            {'counter_name': 'Not Collected', 'instance_name': ''},
            [],
            id='counter absent from the result set submits nothing',
        ),
        pytest.param(
            {'counter_name': 'Log Flushes/sec', 'instance_name': 'tenant_missing'},
            [],
            id='instance absent from the result set submits nothing',
        ),
    ],
)
def test_SqlSimpleMetric_fetch_metric(cfg_overrides, expected):
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = SIMPLE_METRIC_ROWS
    mock_cursor.description = [('counter_name',), ('instance_name',), ('object_name',), ('cntr_value',)]

    report_function = mock.MagicMock()
    cfg_instance = {
        'name': 'sqlserver.test.metric',
        'tags': list(SIMPLE_METRIC_TAGS),
        'hostname': 'stubbed.hostname',
    }
    cfg_instance.update(cfg_overrides)
    metric_obj = SqlSimpleMetric(
        cfg_instance=cfg_instance,
        base_name=None,
        report_function=report_function,
        column=None,
        logger=mock.MagicMock(),
    )

    results, columns = SqlSimpleMetric.fetch_all_values(mock_cursor, [cfg_instance['counter_name']], mock.MagicMock())
    metric_obj.fetch_metric(results, columns)

    assert report_function.call_args_list == [
        mock.call('sqlserver.test.metric', value, raw=True, hostname='stubbed.hostname', tags=tags)
        for value, tags in expected
    ]


def test_get_sql_counter_type_caches_counters_without_a_base(instance_docker):
    """A counter type is immutable for the lifetime of the server, so it should only be queried once.

    Without caching, rebuilding the metric list queries the type of every counter for every
    autodiscovered database, which is hundreds of round trips on an instance with many databases.
    """
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchone.return_value = (PERF_COUNTER_BULK_COUNT,)
    check._connection = mock.MagicMock()
    check._connection.get_managed_cursor.return_value.__enter__.return_value = mock_cursor

    for _ in range(3):
        assert check.get_sql_counter_type('Transactions/sec') == (PERF_COUNTER_BULK_COUNT, None)

    assert mock_cursor.execute.call_count == 1


def test_performance_counter_metrics_share_a_single_query(instance_docker):
    """The performance counter table must be read once per run, for the counters of every class at once.

    Scanning sys.dm_os_performance_counters costs about as much whether it returns two rows or thousands, so
    a query per metric class multiplies the most expensive part of the collection without returning more data.
    """
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.databases = {Database('master')}
    check.instance_per_type_metrics = {
        'SqlSimpleMetric': {'Transactions/sec'},
        'SqlFractionMetric': {'Buffer cache hit ratio', 'Buffer cache hit ratio base'},
        'SqlIncrFractionMetric': {'Average Latch Wait Time (ms)', 'Average Latch Wait Time Base'},
        'SqlOsWaitStat': {'LCK_M_S'},
    }
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = []

    check._fetch_instance_results(mock_cursor)

    executed = [call.args for call in mock_cursor.execute.call_args_list]
    perf_counter_queries = [args for args in executed if DEFAULT_PERFORMANCE_TABLE in args[0]]
    assert len(perf_counter_queries) == 1
    assert sorted(perf_counter_queries[0][1]) == [
        'Average Latch Wait Time (ms)',
        'Average Latch Wait Time Base',
        'Buffer cache hit ratio',
        'Buffer cache hit ratio base',
        'Transactions/sec',
    ]
    # metrics from other tables keep their own query
    assert len([args for args in executed if 'sys.dm_os_wait_stats' in args[0]]) == 1


def _mock_database_list():
    Row = namedtuple('Row', 'name')
    fetchall_results = [
        Row('master'),
        Row('tempdb'),
        Row('msdb'),
        Row('AdventureWorks2017'),
        Row('CaseSensitive2018'),
        Row('Fancy2020db'),
    ]
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = iter(fetchall_results)
    # check excluded overrides included
    mock_cursor.fetchall.return_value = iter(fetchall_results)
    return fetchall_results, mock_cursor


def _mock_database_list_azure():
    Row = namedtuple('Row', ['name', 'physical_database_name'])
    fetchall_results = [
        Row('master', 'master'),
        Row('tempdb', 'tempdb'),
        Row('msdb', 'msdb'),
        Row('AdventureWorks2017', 'fce04774'),
        Row('CaseSensitive2018', 'jub3j8kh'),
        Row('Fancy2020db', '40e688a7e268'),
    ]
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = iter(fetchall_results)
    # check excluded overrides included
    mock_cursor.fetchall.return_value = iter(fetchall_results)
    return fetchall_results, mock_cursor


def test_set_default_driver_conf():
    # Docker Agent with ODBCSYSINI env var
    # The only case where we set ODBCSYSINI to the the default odbcinst.ini folder
    with EnvVars({'DOCKER_DD_AGENT': 'true'}, ignore=['ODBCSYSINI']):
        set_default_driver_conf()
        assert os.environ['ODBCSYSINI'].endswith(os.path.join('data', 'driver_config'))

    with mock.patch("datadog_checks.base.utils.platform.Platform.is_linux", return_value=True):
        with EnvVars({}, ignore=['ODBCSYSINI']):
            set_default_driver_conf()
            assert 'ODBCSYSINI' in os.environ, "ODBCSYSINI should be set"
            assert os.environ['ODBCSYSINI'].endswith(os.path.join('data', 'driver_config'))

    # `set_default_driver_conf` have no effect on the cases below
    with EnvVars({'ODBCSYSINI': 'ABC', 'DOCKER_DD_AGENT': 'true'}):
        set_default_driver_conf()
        assert os.environ['ODBCSYSINI'] == 'ABC'

    with mock.patch("datadog_checks.base.utils.platform.Platform.is_linux", return_value=True):
        with EnvVars({}):
            set_default_driver_conf()
            assert 'ODBCSYSINI' in os.environ
            assert os.environ['ODBCSYSINI'].endswith(os.path.join('tests', 'odbc'))

        with EnvVars({'ODBCSYSINI': 'ABC'}):
            set_default_driver_conf()
            assert os.environ['ODBCSYSINI'] == 'ABC'


@not_windows_ci
def test_set_default_driver_conf_linux():
    odbc_config_dir = os.path.expanduser('~')
    with mock.patch("datadog_checks.sqlserver.utils.get_unixodbc_sysconfig", return_value=odbc_config_dir):
        with EnvVars({}, ignore=['ODBCSYSINI']):
            odbc_inst = os.path.join(odbc_config_dir, "odbcinst.ini")
            odbc_ini = os.path.join(odbc_config_dir, "odbc.ini")
            for file in [odbc_inst, odbc_ini]:
                if os.path.exists(file):
                    os.remove(file)
            with open(odbc_ini, "x") as file:
                file.write("dummy-content")
            set_default_driver_conf()
            assert is_non_empty_file(odbc_inst), "odbc_inst should have been created when a non empty odbc.ini exists"


@windows_ci
def test_check_local(aggregator, dd_run_check, init_config, instance_docker):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    dd_run_check(sqlserver_check)
    check_tags = sqlserver_check._config.tags + [
        "database_hostname:{}".format("stubbed.hostname"),
        "database_instance:{}".format("stubbed.hostname"),
        "dd.internal.resource:database_instance:{}".format("stubbed.hostname"),
        "sqlserver_servername:{}".format(sqlserver_check.static_info_cache[STATIC_INFO_SERVERNAME].lower()),
    ]
    expected_tags = check_tags + [
        'sqlserver_host:{}'.format(sqlserver_check.resolved_hostname),
        'connection_host:{}'.format(DOCKER_SERVER),
        'db:master',
    ]
    assert_metrics(instance_docker, aggregator, check_tags, expected_tags, hostname=sqlserver_check.resolved_hostname)


SQL_SERVER_2012_VERSION_EXAMPLE = """\
Microsoft SQL Server 2012 (SP3) (KB3072779) - 11.0.6020.0 (X64)
    Oct 20 2015 15:36:27
    Copyright (c) Microsoft Corporation
    Express Edition (64-bit) on Windows NT 6.3 <X64> (Build 17763: ) (Hypervisor)
"""

SQL_SERVER_2019_VERSION_EXAMPLE = """\
Microsoft SQL Server 2019 (RTM-CU12) (KB5004524) - 15.0.4153.1 (X64)
    Jul 19 2021 15:37:34
    Copyright (C) 2019 Microsoft Corporation
    Standard Edition (64-bit) on Windows Server 2016 Datacenter 10.0 <X64> (Build 14393: ) (Hypervisor)
"""


@pytest.mark.parametrize(
    "version,expected_year", [(SQL_SERVER_2012_VERSION_EXAMPLE, 2012), (SQL_SERVER_2019_VERSION_EXAMPLE, 2019)]
)
def test_parse_sqlserver_year(version, expected_year):
    assert parse_sqlserver_year(version) == expected_year


@pytest.mark.parametrize(
    "version,expected_major_version", [(SQL_SERVER_2012_VERSION_EXAMPLE, 11), (SQL_SERVER_2019_VERSION_EXAMPLE, 15)]
)
def test_parse_sqlserver_major_version(version, expected_major_version):
    assert parse_sqlserver_major_version(version) == expected_major_version


@pytest.mark.parametrize(
    'marker', ['ddps=', 'dddbs=', 'ddh=', 'dddb=', 'ddprs=', 'dde=', 'ddpv=', 'traceparent=', 'ddsh=']
)
def test_needs_comment_recovery_recognizes_dbm_comment_markers(marker):
    assert needs_comment_recovery(f"(@P1 int)/*{marker}'value'*/ SELECT 1", [])


@pytest.mark.parametrize(
    'full_text,statement_comments,expected',
    [
        pytest.param('(@P1 int)SELECT @P1', [], False, id='rpc_without_comment'),
        pytest.param(
            "/*dddbs='orders-service'*/ SELECT 1",
            ["/*dddbs='orders-service'*/"],
            False,
            id='comment_already_in_statement_metadata',
        ),
        pytest.param("/*dddbs='orders-service'*/ SELECT 1", [], True, id='comment_missing_from_statement_metadata'),
    ],
)
def test_needs_comment_recovery_requires_missing_dbm_comment(full_text, statement_comments, expected):
    assert needs_comment_recovery(full_text, statement_comments) is expected


@pytest.mark.parametrize(
    "instance_host,split_host,split_port",
    [
        ("localhost,1433,some-typo", "localhost", "1433"),
        ("localhost, 1433,some-typo", "localhost", "1433"),
        ("localhost,1433", "localhost", "1433"),
        ("localhost", "localhost", None),
    ],
)
def test_split_sqlserver_host(instance_host, split_host, split_port):
    s_host, s_port = split_sqlserver_host_port(instance_host)
    assert (s_host, s_port) == (split_host, split_port)


AGENT_HOSTNAME = 'sql-agent-host.example.com'


@pytest.fixture
def agent_hostname_for_resolve_db_host():
    datadog_agent.set_hostname(AGENT_HOSTNAME)
    yield
    datadog_agent.reset_hostname()


@pytest.mark.parametrize(
    'instance_host,host_part',
    [
        (r'SQL-HOST01\INSTANCE01,1601', r'SQL-HOST01\INSTANCE01'),
        (r'MY-SERVER\SQLEXPRESS,1433', r'MY-SERVER\SQLEXPRESS'),
        (r'MY-SERVER\SQLEXPRESS', r'MY-SERVER\SQLEXPRESS'),
    ],
)
def test_resolve_db_host_named_instance_returns_agent_hostname(
    agent_hostname_for_resolve_db_host, instance_host, host_part
):
    instance = {
        'host': instance_host,
        'username': 'datadog',
        'password': 'secret',
    }
    check = SQLServer(CHECK_NAME, {}, [instance])
    assert check.host == host_part

    # Agent 7.79+ base resolver returns the literal host string for unresolvable names.
    with mock.patch(
        'datadog_checks.sqlserver.sqlserver.agent_host_resolver',
        return_value=host_part,
    ):
        assert check.resolve_db_host() == AGENT_HOSTNAME
    assert check.resolved_hostname == AGENT_HOSTNAME
    assert check.database_hostname == AGENT_HOSTNAME


@pytest.mark.parametrize(
    'instance_host,host_part,base_resolver_return',
    [
        ('db.example.com,1433', 'db.example.com', 'resolved-db.example.com'),
        ('192.0.2.10,1433', '192.0.2.10', '192.0.2.10'),
    ],
)
def test_resolve_db_host_plain_host_delegates_to_base_resolver(
    agent_hostname_for_resolve_db_host, instance_host, host_part, base_resolver_return
):
    instance = {
        'host': instance_host,
        'username': 'datadog',
        'password': 'secret',
    }
    check = SQLServer(CHECK_NAME, {}, [instance])
    assert check.host == host_part

    with mock.patch(
        'datadog_checks.sqlserver.sqlserver.agent_host_resolver',
        return_value=base_resolver_return,
    ) as mock_resolver:
        assert check.resolve_db_host() == base_resolver_return
        mock_resolver.assert_called_once_with(host_part)


@pytest.mark.parametrize(
    "query,expected_comments,is_proc,expected_name",
    [
        [
            None,
            [],
            False,
            None,
        ],
        [
            "",
            [],
            False,
            None,
        ],
        [
            "/*",
            [],
            False,
            None,
        ],
        [
            "--",
            [],
            False,
            None,
        ],
        [
            "/*justonecomment*/",
            ["/*justonecomment*/"],
            False,
            None,
        ],
        [
            """\
            /* a comment */
            -- Single comment
            """,
            ["/* a comment */", "-- Single comment"],
            False,
            None,
        ],
        [
            "/*tag=foo*/ SELECT * FROM foo;",
            ["/*tag=foo*/"],
            False,
            None,
        ],
        [
            "/*tag=foo*/ SELECT * FROM /*other=tag,incomment=yes*/ foo;",
            ["/*tag=foo*/", "/*other=tag,incomment=yes*/"],
            False,
            None,
        ],
        [
            "/*tag=foo*/ SELECT * FROM /*other=tag,incomment=yes*/ foo /*lastword=yes*/",
            ["/*tag=foo*/", "/*other=tag,incomment=yes*/", "/*lastword=yes*/"],
            False,
            None,
        ],
        [
            """\
            -- My Comment
            CREATE PROCEDURE bobProcedure
            BEGIN
                SELECT name FROM bob
            END;
            """,
            ["-- My Comment"],
            True,
            "bobProcedure",
        ],
        [
            """\
            -- My procedure
            CREATE PROCEDURE bobProcedure
            BEGIN
                SELECT name FROM bob
            END;
            """,
            ["-- My procedure"],
            True,
            "bobProcedure",
        ],
        [
            """\
            -- My Comment
            CREATE PROCEDURE bobProcedure
            -- In the middle
            BEGIN
                SELECT name FROM bob
            END;
            """,
            ["-- My Comment", "-- In the middle"],
            True,
            "bobProcedure",
        ],
        [
            """\
            -- My Comment
            CREATE PROCEDURE bobProcedure
            -- this procedure does foo
            BEGIN
                SELECT name FROM bob
            END;
            """,
            ["-- My Comment", "-- this procedure does foo"],
            True,
            "bobProcedure",
        ],
        [
            """\
            -- My Comment
            CREATE PROCEDURE bobProcedure
            -- In the middle
            BEGIN
                SELECT name FROM bob
            END;
            -- And at the end
            """,
            ["-- My Comment", "-- In the middle", "-- And at the end"],
            True,
            "bobProcedure",
        ],
        [
            """\
            -- My Comment
            CREATE PROCEDURE bobProcedure
            -- In the middle
            /*mixed with mult-line foo*/
            BEGIN
                SELECT name FROM bob
            END;
            -- And at the end
            """,
            ["-- My Comment", "-- In the middle", "/*mixed with mult-line foo*/", "-- And at the end"],
            True,
            "bobProcedure",
        ],
        [
            """\
            -- My procedure
            CREATE PROCEDURE bobProcedure
            -- In the middle
            /*mixed with procedure foo*/
            BEGIN
                SELECT name FROM bob
            END;
            -- And at the end
            """,
            ["-- My procedure", "-- In the middle", "/*mixed with procedure foo*/", "-- And at the end"],
            True,
            "bobProcedure",
        ],
        [
            """\
            /* hello
            this is a mult-line-comment
            tag=foo,blah=tag
            */
            /*
            second multi-line
            comment
            */
            CREATE PROCEDURE bobProcedure
            BEGIN
                SELECT name FROM bob
            END;
            -- And at the end
            """,
            [
                "/* hello this is a mult-line-comment tag=foo,blah=tag */",
                "/* second multi-line comment */",
                "-- And at the end",
            ],
            True,
            "bobProcedure",
        ],
        [
            """\
            /* hello
            this is a mult-line-comment
            tag=foo,blah=tag
            */
            /*
            second multi-line
            for procedure foo
            */
            CREATE PROCEDURE bobProcedure
            BEGIN
                SELECT name FROM bob
            END;
            -- And at the end
            """,
            [
                "/* hello this is a mult-line-comment tag=foo,blah=tag */",
                "/* second multi-line for procedure foo */",
                "-- And at the end",
            ],
            True,
            "bobProcedure",
        ],
        [
            """\
            /* hello
            this is a mult-line-commet
            tag=foo,blah=tag
            */
            CREATE PROCEDURE bobProcedure
            -- In the middle
            /*mixed with mult-line foo*/
            BEGIN
                SELECT name FROM bob
            END;
            -- And at the end
            """,
            [
                "/* hello this is a mult-line-commet tag=foo,blah=tag */",
                "-- In the middle",
                "/*mixed with mult-line foo*/",
                "-- And at the end",
            ],
            True,
            "bobProcedure",
        ],
    ],
)
def test_extract_sql_comments_and_procedure_name(query, expected_comments, is_proc, expected_name):
    comments, p, name = extract_sql_comments_and_procedure_name(query)
    assert comments == expected_comments
    assert p == is_proc
    assert re.match(name, expected_name, re.IGNORECASE) if expected_name else expected_name == name


def test_get_unixodbc_sysconfig():
    etc_dir = os.path.sep
    for dir in ["opt", "datadog-agent", "embedded", "bin", "python"]:
        etc_dir = os.path.join(etc_dir, dir)
    assert get_unixodbc_sysconfig(etc_dir).split(os.path.sep) == [
        "",
        "opt",
        "datadog-agent",
        "embedded",
        "etc",
    ], "incorrect unix odbc config dir"


@pytest.mark.parametrize(
    'template, expected, tags',
    [
        ('$resolved_hostname', 'stubbed.hostname', ['env:prod']),
        ('$env-$resolved_hostname:$port', 'prod-stubbed.hostname:22', ['env:prod', 'port:1']),
        ('$env-$resolved_hostname', 'prod-stubbed.hostname', ['env:prod']),
        ('$env-$resolved_hostname', '$env-stubbed.hostname', []),
        ('$env-$resolved_hostname', 'prod-stubbed.hostname', ['env:prod']),
        ('$env-$server_name/$instance_name', 'prod-server/instance', ['env:prod']),
        ('$full_server_name', 'server\\instance', ['env:prod']),
    ],
)
def test_database_identifier(instance_docker, template, expected, tags):
    """
    Test functionality of calculating database_identifier
    """
    instance_docker['host'] = 'localhost,22'
    instance_docker['database_identifier'] = {'template': template}
    instance_docker['tags'] = tags
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.static_info_cache[STATIC_INFO_SERVERNAME] = 'server'
    check.static_info_cache[STATIC_INFO_INSTANCENAME] = 'instance'
    check.static_info_cache[STATIC_INFO_FULL_SERVERNAME] = 'server\\instance'
    # Reset for recalculation with static info
    check._database_identifier = None

    assert check.database_identifier == expected


def test_only_custom_queries_validation_warnings(caplog):
    """Test that appropriate warning logs are emitted when only_custom_queries conflicts with other configurations."""
    from datadog_checks.sqlserver.config import SQLServerConfig

    caplog.clear()
    caplog.set_level(logging.WARNING)

    # Use a real logger that will be captured by caplog
    real_logger = logging.getLogger('test_sqlserver_config')

    # Test case 1: only_custom_queries with DBM enabled
    instance_with_dbm = {
        'host': 'localhost',
        'username': 'test',
        'password': 'test',
        'only_custom_queries': True,
        'dbm': True,
        'custom_queries': [
            {
                'query': "SELECT 1 as test_value",
                'columns': [{'name': 'test_value', 'type': 'gauge'}],
                'tags': ['test:dbm_warning'],
            }
        ],
    }

    config = SQLServerConfig({}, instance_with_dbm, real_logger)
    config._validate_only_custom_queries(instance_with_dbm)

    # Check for DBM warning
    dbm_warning_found = any("only_custom_queries is enabled with DBM" in record.message for record in caplog.records)
    assert dbm_warning_found, "Expected warning about only_custom_queries with DBM not found"

    # Test case 2: only_custom_queries with stored procedure
    caplog.clear()
    instance_with_proc = {
        'host': 'localhost',
        'username': 'test',
        'password': 'test',
        'only_custom_queries': True,
        'stored_procedure': 'pyStoredProc',
        'custom_queries': [
            {
                'query': "SELECT 1 as test_value",
                'columns': [{'name': 'test_value', 'type': 'gauge'}],
                'tags': ['test:proc_warning'],
            }
        ],
    }

    config = SQLServerConfig({}, instance_with_proc, real_logger)
    config._validate_only_custom_queries(instance_with_proc)

    # Check for stored procedure warning
    proc_warning_found = any("`stored_procedure` is deprecated" in record.message for record in caplog.records)
    assert proc_warning_found, "Expected warning about only_custom_queries with stored_procedure not found"

    # Test case 3: only_custom_queries with no custom queries defined
    caplog.clear()
    instance_no_queries = {
        'host': 'localhost',
        'username': 'test',
        'password': 'test',
        'only_custom_queries': True,
        'custom_queries': [],
    }

    config = SQLServerConfig({}, instance_no_queries, real_logger)
    config._validate_only_custom_queries(instance_no_queries)

    # Check for no custom queries warning
    no_queries_warning_found = any(
        "only_custom_queries is enabled but no custom queries are defined" in record.message
        for record in caplog.records
    )
    assert no_queries_warning_found, "Expected warning about only_custom_queries with no custom queries not found"

    # Test case 4: only_custom_queries with all conflicts (should emit all warnings)
    caplog.clear()
    instance_all_conflicts = {
        'host': 'localhost',
        'username': 'test',
        'password': 'test',
        'only_custom_queries': True,
        'dbm': True,
        'stored_procedure': 'pyStoredProc',
        'custom_queries': [],
    }

    config = SQLServerConfig({}, instance_all_conflicts, real_logger)
    config._validate_only_custom_queries(instance_all_conflicts)

    # Check that all three warnings are emitted
    dbm_warning_found = any("only_custom_queries is enabled with DBM" in record.message for record in caplog.records)
    proc_warning_found = any("`stored_procedure` is deprecated" in record.message for record in caplog.records)
    no_queries_warning_found = any(
        "only_custom_queries is enabled but no custom queries are defined" in record.message
        for record in caplog.records
    )

    assert dbm_warning_found, "Expected warning about only_custom_queries with DBM not found in all-conflicts test"
    assert proc_warning_found, (
        "Expected warning about only_custom_queries with stored_procedure not found in all-conflicts test"
    )
    assert no_queries_warning_found, (
        "Expected warning about only_custom_queries with no custom queries not found in all-conflicts test"
    )

    # Test case 5: only_custom_queries with no conflicts (should emit no warnings)
    caplog.clear()
    instance_no_conflicts = {
        'host': 'localhost',
        'username': 'test',
        'password': 'test',
        'only_custom_queries': True,
        'dbm': False,
        'custom_queries': [
            {
                'query': "SELECT 1 as test_value",
                'columns': [{'name': 'test_value', 'type': 'gauge'}],
                'tags': ['test:no_conflicts'],
            }
        ],
    }

    config = SQLServerConfig({}, instance_no_conflicts, real_logger)
    config._validate_only_custom_queries(instance_no_conflicts)

    # Check that no warnings are emitted
    warning_count = len([record for record in caplog.records if record.levelno >= logging.WARNING])
    warning_messages = [record.message for record in caplog.records if record.levelno >= logging.WARNING]
    assert warning_count == 0, f"Expected no warnings but found {warning_count} warnings: {warning_messages}"


@pytest.mark.parametrize(
    'exclude_hostname, expected_hostname',
    [
        (False, 'resolved.hostname'),
        (True, None),
    ],
)
def test_debug_stats_kwargs_respects_exclude_hostname(exclude_hostname, expected_hostname):
    instance = {
        'host': DOCKER_SERVER,
        'username': 'sa',
        'password': 'Password12!',
        'exclude_hostname': exclude_hostname,
    }
    with mock.patch('datadog_checks.sqlserver.SQLServer.resolve_db_host', return_value='resolved.hostname'):
        check = SQLServer(CHECK_NAME, {}, [instance])
    assert check.debug_stats_kwargs()['hostname'] == expected_hostname


DBM_JOB_NAMES = [
    'query-metrics',
    'procedure-metrics',
    'database-metadata',
    'query-activity',
    'agent-jobs-history',
    'deadlocks',
]


@pytest.mark.parametrize(
    'dbm, data_observability_enabled, expected_jobs',
    [
        (False, False, []),
        (False, True, ['data-observability']),
        (True, False, DBM_JOB_NAMES),
        (True, True, DBM_JOB_NAMES + ['data-observability']),
    ],
    ids=['neither', 'data-observability-only', 'dbm-only', 'both'],
)
def test_async_job_registry_matches_config(instance_docker, dbm, data_observability_enabled, expected_jobs):
    """Only the jobs enabled by the instance config are built and registered.

    Data observability is deliberately outside the DBM gate: it collects for instances that have
    not turned DBM on. Every other job requires DBM, and each one's own enabled flag defaults to
    true, so without the gate a non-DBM instance would start collecting.
    """
    instance_docker['dbm'] = dbm
    instance_docker['data_observability'] = {'enabled': data_observability_enabled, 'queries': []}

    check = SQLServer(CHECK_NAME, {}, [instance_docker])

    registered = check._async_job_registry
    assert list(registered) == expected_jobs
    assert check.statement_metrics is registered.get('query-metrics')
    assert check.procedure_metrics is registered.get('procedure-metrics')
    assert check.sql_metadata is registered.get('database-metadata')
    assert check.activity is registered.get('query-activity')
    assert check.agent_history is registered.get('agent-jobs-history')
    assert check.deadlocks is registered.get('deadlocks')
    assert check.data_observability is registered.get('data-observability')


@pytest.mark.parametrize('dbm', [True, False], ids=['dbm', 'no-dbm'])
def test_xe_session_handlers_registered_only_with_dbm(instance_docker, dbm):
    """XE handlers are built during check initialization, so they have to register themselves.

    They only ever ran under the DBM gate in check(), so a non-DBM instance must not get them.
    """
    instance_docker['dbm'] = dbm
    instance_docker['xe_collection'] = {'query_completions': {'enabled': True}, 'query_errors': {'enabled': True}}
    check = SQLServer(CHECK_NAME, {}, [instance_docker])

    check.initialize_xe_session_handlers()

    expected = ['xe_datadog_query_completions', 'xe_datadog_query_errors'] if dbm else []
    assert [handler.job_name for handler in check.xe_session_handlers] == expected
    assert [name for name in check._async_job_registry if name.startswith('xe_')] == expected


@pytest.mark.parametrize(
    'job_attr, invoke',
    [
        ('statement_metrics', lambda job: job.collect_statement_metrics_and_plans()),
        ('procedure_metrics', lambda job: job.collect_procedure_metrics()),
        ('sql_metadata', lambda job: job.report_sqlserver_metadata()),
        ('activity', lambda job: job.collect_activity()),
        ('agent_history', lambda job: job.collect_agent_history()),
        ('deadlocks', lambda job: job._query_deadlocks()),
    ],
)
def test_job_aborts_collection_when_cancelled(instance_docker, job_attr, invoke):
    """A cancelled job must stop before it queries.

    Teardown waits for the job loop, so a tick that works through its remaining queries after a
    cancel holds up the Agent's unschedule for as long as those queries take.
    """
    instance_docker['dbm'] = True
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    job = getattr(check, job_attr)
    job.cancel()
    check._connection = mock.MagicMock()

    with pytest.raises(Exception, match='cancelled'):
        invoke(job)

    check._connection.open_managed_default_connection.assert_not_called()


def _build_run_state(check):
    """Bring a freshly constructed check up to the state a collection leaves it in.

    Everything here is built lazily by ``check()``, and each piece holds the check, so without it
    the reclaim test would pass while the real teardown still leaked.
    """
    check.initialize_xe_session_handlers()
    check._query_manager = QueryManager(check, check.execute_query_raw)
    assert check.database_metrics
    check.instance_metrics = [
        check.typed_metric(
            cfg_inst={'name': 'sqlserver.stats.connections', 'counter_name': 'User Connections', 'tags': []},
            table=DEFAULT_PERFORMANCE_TABLE,
            sql_counter_type=PERF_COUNTER_BULK_COUNT,
        )
    ]


def test_check_gc_after_cancel(instance_docker):
    """Verify cancel() breaks all reference cycles so refcount alone reclaims the check.

    If this test fails, the assertion message lists the types still holding a
    reference to the check. To fix it:

    1. Identify the referrer type in the failure message (e.g. ``QueryManager``).
    2. Find which attribute on that object points back to the check (usually
       ``self.check`` or ``self._check``).
    3. Null that attribute in the check's ``shutdown()`` or in the relevant job's
       ``shutdown()``.
    4. If the referrer is a closure or ``functools.partial``, find the
       registration site and null or clear the container that holds it.
    """
    instance_docker['dbm'] = True
    instance_docker['xe_collection'] = {'query_completions': {'enabled': True}, 'query_errors': {'enabled': True}}
    instance_docker['data_observability'] = {'enabled': True, 'queries': []}

    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    _build_run_state(check)
    ref = weakref.ref(check)

    check.cancel()

    gc.collect()
    gc.disable()
    try:
        del check
        obj = ref()
        if obj is not None:
            referrers = [
                f"bound method {r.__qualname__}" if inspect.ismethod(r) else type(r).__name__
                for r in gc.get_referrers(obj)
            ]
            del obj
            pytest.fail(f"Check still alive after cancel() + del -- pinned by: {referrers}")
    finally:
        gc.enable()
