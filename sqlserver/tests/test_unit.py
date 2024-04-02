# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import re
from collections import namedtuple

import mock
import pytest

from datadog_checks.dev import EnvVars
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.connection import split_sqlserver_host_port
from datadog_checks.sqlserver.metrics import SqlFractionMetric, SqlMasterDatabaseFileStats
from datadog_checks.sqlserver.sqlserver import SQLConnectionError
from datadog_checks.sqlserver.utils import (
    Database,
    extract_sql_comments_and_procedure_name,
    parse_sqlserver_major_version,
    set_default_driver_conf,
)

from .common import CHECK_NAME, DOCKER_SERVER, assert_metrics
from .utils import windows_ci

# mark the whole module
pytestmark = pytest.mark.unit


def test_get_cursor(instance_docker):
    """
    Ensure we don't leak connection info in case of a KeyError when the
    connection pool is empty or the params for `get_cursor` are invalid.
    """
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()
    with pytest.raises(SQLConnectionError):
        check.connection.get_cursor('foo')


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


@pytest.mark.parametrize(
    'col_val_row_1, col_val_row_2, col_val_row_3',
    [
        pytest.param(256, 1024, 1720, id='Valid column value 0'),
        pytest.param(0, None, 1024, id='NoneType column value 1, should not raise error'),
        pytest.param(512, 0, 256, id='Valid column value 2'),
        pytest.param(None, 256, 0, id='NoneType column value 3, should not raise error'),
    ],
)
def test_SqlMasterDatabaseFileStats_fetch_metric(col_val_row_1, col_val_row_2, col_val_row_3):
    Row = namedtuple('Row', ['name', 'file_id', 'type', 'physical_name', 'size', 'max_size', 'state', 'state_desc'])
    mock_rows = [
        Row('master', 1, 0, '/var/opt/mssql/data/master.mdf', col_val_row_1, -1, 0, 'ONLINE'),
        Row('tempdb', 1, 0, '/var/opt/mssql/data/tempdb.mdf', col_val_row_2, -1, 0, 'ONLINE'),
        Row('msdb', 1, 0, '/var/opt/mssql/data/MSDBData.mdf', col_val_row_3, -1, 0, 'ONLINE'),
    ]
    mock_cols = ['name', 'file_id', 'type', 'physical_name', 'size', 'max_size', 'state', 'state_desc']
    mock_metric_obj = SqlMasterDatabaseFileStats(
        cfg_instance=mock.MagicMock(dict),
        base_name=None,
        report_function=mock.MagicMock(),
        column='size',
        logger=None,
    )
    with mock.patch.object(
        SqlMasterDatabaseFileStats, 'fetch_metric', wraps=mock_metric_obj.fetch_metric
    ) as mock_fetch_metric:
        errors = 0
        try:
            mock_fetch_metric(mock_rows, mock_cols)
        except Exception as e:
            errors += 1
            raise AssertionError('{}'.format(e))
        assert errors < 1


@pytest.mark.parametrize(
    'base_name',
    [
        pytest.param('Buffer cache hit ratio base', id='base_name valid'),
        pytest.param(None, id='base_name None'),
    ],
)
def test_SqlFractionMetric_base(caplog, base_name):
    Row = namedtuple('Row', ['counter_name', 'cntr_type', 'cntr_value', 'instance_name', 'object_name'])
    fetchall_results = [
        Row('Buffer cache hit ratio', 537003264, 33453, '', 'SQLServer:Buffer Manager'),
        Row('Buffer cache hit ratio base', 1073939712, 33531, '', 'SQLServer:Buffer Manager'),
        Row('some random counter', 1073939712, 1111, '', 'SQLServer:Buffer Manager'),
        Row('some random counter base', 1073939712, 33531, '', 'SQLServer:Buffer Manager'),
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
    Row = namedtuple('Row', ['counter_name', 'cntr_type', 'cntr_value', 'instance_name', 'object_name'])
    fetchall_results = [
        Row('Buffer cache hit ratio', 537003264, 33453, '', 'SQLServer:Buffer Manager'),
        Row('Buffer cache hit ratio base', 1073939712, 33531, '', 'SQLServer:Buffer Manager'),
        Row('Foo counter', 537003264, 1, 'bar', 'SQLServer:Buffer Manager'),
        Row('Foo counter base', 1073939712, 50, 'bar', 'SQLServer:Buffer Manager'),
        Row('Foo counter', 537003264, 5, 'zoo', 'SQLServer:Buffer Manager'),
        Row('Foo counter base', 1073939712, 100, 'zoo', 'SQLServer:Buffer Manager'),
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

    # `set_default_driver_conf` have no effect on the cases below
    with EnvVars({'ODBCSYSINI': 'ABC', 'DOCKER_DD_AGENT': 'true'}):
        set_default_driver_conf()
        assert os.environ['ODBCSYSINI'] == 'ABC'

    with EnvVars({}, ignore=['ODBCSYSINI']):
        set_default_driver_conf()
        assert 'ODBCSYSINI' not in os.environ

    with EnvVars({'ODBCSYSINI': 'ABC'}):
        set_default_driver_conf()
        assert os.environ['ODBCSYSINI'] == 'ABC'


@windows_ci
def test_check_local(aggregator, dd_run_check, init_config, instance_docker):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    dd_run_check(sqlserver_check)
    check_tags = instance_docker.get('tags', [])
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
    "version,expected_major_version", [(SQL_SERVER_2012_VERSION_EXAMPLE, 2012), (SQL_SERVER_2019_VERSION_EXAMPLE, 2019)]
)
def test_parse_sqlserver_major_version(version, expected_major_version):
    assert parse_sqlserver_major_version(version) == expected_major_version


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


def test_database_state(aggregator, dd_run_check, init_config, instance_docker):
    instance_docker['database'] = 'mAsTeR'
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    dd_run_check(sqlserver_check)
    expected_tags = instance_docker.get('tags', []) + [
        'database_recovery_model_desc:SIMPLE',
        'database_state_desc:ONLINE',
        'database:{}'.format(instance_docker['database']),
        'db:{}'.format(instance_docker['database']),
    ]
    aggregator.assert_metric('sqlserver.database.state', tags=expected_tags, hostname=sqlserver_check.resolved_hostname)


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
