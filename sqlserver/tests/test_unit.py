# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
from collections import namedtuple

import mock
import pytest

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.dev import EnvVars
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.connection import split_sqlserver_host_port
from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_SQL_DATABASE,
    ENGINE_EDITION_STANDARD,
    STATIC_INFO_ENGINE_EDITION,
)
from datadog_checks.sqlserver.metrics import SqlMasterDatabaseFileStats
from datadog_checks.sqlserver.sqlserver import SQLConnectionError
from datadog_checks.sqlserver.utils import Database, parse_sqlserver_major_version, set_default_driver_conf

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
    with mock.patch('datadog_checks.sqlserver.connection.Connection.check_database', return_value=(False, 'db')):
        with pytest.raises(ConfigurationError):
            check = SQLServer(CHECK_NAME, {}, [instance])
            check.initialize_connection()

    instance['ignore_missing_database'] = True
    with mock.patch('datadog_checks.sqlserver.connection.Connection.check_database', return_value=(False, 'db')):
        check = SQLServer(CHECK_NAME, {}, [instance])
        check.initialize_connection()
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
    mock_results.__iter__.return_value = db_results
    get_cursor.return_value = mock_results

    instance = copy.copy(instance_docker_defaults)
    # make sure check doesn't try to add metrics
    instance['stored_procedure'] = 'fake_proc'

    # check base case of lowercase for lowercase and case-insensitive db
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    assert check.do_check is True

    # check all caps for case insensitive db
    instance['database'] = 'MASTER'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    assert check.do_check is True

    # check mixed case against mixed case but case-insensitive db
    instance['database'] = 'AdventureWORKS2017'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    assert check.do_check is True

    # check case sensitive but matched db
    instance['database'] = 'CaseSensitive2018'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    assert check.do_check is True

    # check case sensitive but mismatched db
    instance['database'] = 'cASEsENSITIVE2018'
    check = SQLServer(CHECK_NAME, {}, [instance])
    with pytest.raises(ConfigurationError):
        check.initialize_connection()

    # check offline but exists db
    instance['database'] = 'Offlinedb'
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    assert check.do_check is True


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


def _mock_database_list():
    Row = namedtuple('Row', 'name')
    fetchall_results = [
        Row('master'),
        Row('tempdb'),
        Row('model'),
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
        Row('model', 'model'),
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
    expected_tags = check_tags + ['sqlserver_host:{}'.format(DOCKER_SERVER), 'db:master']
    assert_metrics(aggregator, check_tags, expected_tags, hostname=sqlserver_check.resolved_hostname)


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


@pytest.mark.parametrize(
    "dbm_enabled, instance_host, database, reported_hostname, engine_edition, expected_hostname",
    [
        (False, 'localhost,1433,some-typo', None, '', ENGINE_EDITION_STANDARD, 'stubbed.hostname'),
        (True, 'localhost,1433', None, '', ENGINE_EDITION_STANDARD, 'stubbed.hostname'),
        (False, 'localhost', None, '', ENGINE_EDITION_STANDARD, 'stubbed.hostname'),
        (False, '8.8.8.8', None, '', ENGINE_EDITION_STANDARD, 'stubbed.hostname'),
        (True, 'localhost', None, 'forced_hostname', ENGINE_EDITION_STANDARD, 'forced_hostname'),
        (True, 'datadoghq.com,1433', None, '', ENGINE_EDITION_STANDARD, 'datadoghq.com'),
        (True, 'datadoghq.com', None, '', ENGINE_EDITION_STANDARD, 'datadoghq.com'),
        (True, 'datadoghq.com', None, 'forced_hostname', ENGINE_EDITION_STANDARD, 'forced_hostname'),
        (True, '8.8.8.8,1433', None, '', ENGINE_EDITION_STANDARD, '8.8.8.8'),
        (False, '8.8.8.8', None, 'forced_hostname', ENGINE_EDITION_STANDARD, 'forced_hostname'),
        (True, 'foo.database.windows.net', None, None, ENGINE_EDITION_SQL_DATABASE, 'foo/master'),
        (True, 'foo.database.windows.net', 'master', None, ENGINE_EDITION_SQL_DATABASE, 'foo/master'),
        (True, 'foo.database.windows.net', 'bar', None, ENGINE_EDITION_SQL_DATABASE, 'foo/bar'),
        (
            True,
            'foo.database.windows.net',
            'bar',
            'override-reported',
            ENGINE_EDITION_SQL_DATABASE,
            'override-reported',
        ),
        (True, 'foo-custom-dns', 'bar', None, ENGINE_EDITION_SQL_DATABASE, 'foo-custom-dns/bar'),
    ],
)
def test_resolved_hostname(dbm_enabled, instance_host, database, reported_hostname, engine_edition, expected_hostname):
    instance = {
        'host': instance_host,
        'dbm': dbm_enabled,
    }
    if database:
        instance['database'] = database
    if reported_hostname:
        instance['reported_hostname'] = reported_hostname
    sqlserver_check = SQLServer(CHECK_NAME, {}, [instance])
    sqlserver_check.static_info_cache[STATIC_INFO_ENGINE_EDITION] = engine_edition
    sqlserver_check._resolved_hostname = None
    assert sqlserver_check.resolved_hostname == expected_hostname


def test_database_state(aggregator, dd_run_check, init_config, instance_docker):
    instance_docker['database'] = 'mAsTeR'
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    dd_run_check(sqlserver_check)
    expected_tags = instance_docker.get('tags', []) + [
        'database_recovery_model_desc:SIMPLE',
        'database_state_desc:ONLINE',
        'database:{}'.format(instance_docker['database']),
    ]
    aggregator.assert_metric('sqlserver.database.state', tags=expected_tags, hostname=sqlserver_check.resolved_hostname)
