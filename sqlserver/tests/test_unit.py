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
from datadog_checks.sqlserver.sqlserver import SQLConnectionError
from datadog_checks.sqlserver.utils import set_default_driver_conf

from .common import CHECK_NAME, LOCAL_SERVER, assert_metrics
from .utils import windows_ci

# mark the whole module
pytestmark = pytest.mark.unit


def test_get_cursor(instance_sql):
    """
    Ensure we don't leak connection info in case of a KeyError when the
    connection pool is empty or the params for `get_cursor` are invalid.
    """
    check = SQLServer(CHECK_NAME, {}, [instance_sql])
    check.initialize_connection()
    with pytest.raises(SQLConnectionError):
        check.connection.get_cursor('foo')


def test_missing_db(instance_sql, dd_run_check):
    instance = copy.copy(instance_sql)
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
def test_db_exists(get_cursor, mock_connect, instance_sql, dd_run_check):
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

    instance = copy.copy(instance_sql)
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
    all_dbs = set([r.name for r in fetchall_results])
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


def test_autodiscovery_matches_some(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list()
    instance_autodiscovery['autodiscovery_include'] = ['master', 'fancy2020db', 'missingdb', 'fakedb']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    assert check.databases == set(['master', 'Fancy2020db'])


def test_autodiscovery_exclude_some(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list()
    instance_autodiscovery['autodiscovery_include'] = ['.*']  # replace default `.*`
    instance_autodiscovery['autodiscovery_exclude'] = ['.*2020db$', 'm.*']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    assert check.databases == set(['tempdb', 'AdventureWorks2017', 'CaseSensitive2018'])


def test_autodiscovery_exclude_override(instance_autodiscovery):
    fetchall_results, mock_cursor = _mock_database_list()
    instance_autodiscovery['autodiscovery_include'] = ['t.*', 'master']  # remove default `.*`
    instance_autodiscovery['autodiscovery_exclude'] = ['.*2020db$', 'm.*']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    check.autodiscover_databases(mock_cursor)
    assert check.databases == set(['tempdb'])


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
def test_check_local(aggregator, dd_run_check, init_config, instance_sql):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_sql])
    dd_run_check(sqlserver_check)
    expected_tags = instance_sql.get('tags', []) + ['sqlserver_host:{}'.format(LOCAL_SERVER), 'db:master']
    assert_metrics(aggregator, expected_tags)


@windows_ci
@pytest.mark.parametrize('adoprovider', ['SQLOLEDB', 'SQLNCLI11'])
def test_check_adoprovider(aggregator, dd_run_check, init_config, instance_sql, adoprovider):
    instance = copy.deepcopy(instance_sql)
    instance['adoprovider'] = adoprovider

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance])
    dd_run_check(sqlserver_check)
    expected_tags = instance.get('tags', []) + ['sqlserver_host:{}'.format(LOCAL_SERVER), 'db:master']
    assert_metrics(aggregator, expected_tags)
