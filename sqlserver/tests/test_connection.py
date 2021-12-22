# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import mock
import pyodbc
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.connection import Connection

from .common import CHECK_NAME
from .utils import not_windows_ci, windows_ci

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'connector, param',
    [
        pytest.param('odbc', 'adoprovider', id='Provider is ignored when using odbc'),
        pytest.param('adodbapi', 'dsn', id='DSN is ignored when using adodbapi'),
        pytest.param('adodbapi', 'driver', id='Driver is ignored when using adodbapi'),
    ],
)
def test_will_warn_parameters_for_the_wrong_connection(instance_sql_defaults, connector, param):
    instance_sql_defaults.update({'connector': connector, param: 'foo'})
    connection = Connection({}, instance_sql_defaults, None)
    connection.log = mock.MagicMock()
    connection._connection_options_validation('somekey', 'somedb')
    connection.log.warning.assert_called_once_with(
        "%s option will be ignored since %s connection is used", param, connector
    )


@pytest.mark.parametrize(
    'connector, cs, param',
    [
        pytest.param('odbc', 'DSN', 'dsn', id='Cannot define DSN twice'),
        pytest.param('odbc', 'DRIVER', 'driver', id='Cannot define DRIVER twice'),
        pytest.param('odbc', 'SERVER', 'host', id='Cannot define DRIVER twice'),
        pytest.param('odbc', 'UID', 'username', id='Cannot define UID twice'),
        pytest.param('odbc', 'PWD', 'password', id='Cannot define PWD twice'),
        pytest.param('adodbapi', 'PROVIDER', 'adoprovider', id='Cannot define PROVIDER twice'),
        pytest.param('adodbapi', 'Data Source', 'host', id='Cannot define Data Source twice'),
        pytest.param('adodbapi', 'User ID', 'username', id='Cannot define User ID twice'),
        pytest.param('adodbapi', 'Password', 'password', id='Cannot define Password twice'),
    ],
)
def test_will_fail_for_duplicate_parameters(instance_sql_defaults, connector, cs, param):
    instance_sql_defaults.update({'connector': connector, param: 'foo', 'connection_string': cs + "=foo"})
    connection = Connection({}, instance_sql_defaults, None)
    match = (
        "%s has been provided both in the connection string and as a configuration option (%s), "
        "please specify it only once" % (cs, param)
    )

    with pytest.raises(ConfigurationError, match=re.escape(match)):
        connection._connection_options_validation('somekey', 'somedb')


@pytest.mark.parametrize(
    'connector, cs',
    [
        pytest.param('adodbapi', 'DSN', id='Cannot define DSN for adodbapi'),
        pytest.param('adodbapi', 'DRIVER', id='Cannot define DRIVER for adodbapi'),
        pytest.param('adodbapi', 'SERVER', id='Cannot define DRIVER for adodbapi'),
        pytest.param('adodbapi', 'UID', id='Cannot define UID for adodbapi'),
        pytest.param('adodbapi', 'PWD', id='Cannot define PWD for adodbapi'),
        pytest.param('odbc', 'PROVIDER', id='Cannot define PROVIDER for odbc'),
        pytest.param('odbc', 'Data Source', id='Cannot define Data source for odbc'),
        pytest.param('odbc', 'User ID', id='Cannot define User ID for odbc'),
        pytest.param('odbc', 'Password', id='Cannot define Password for odbc'),
    ],
)
def test_will_fail_for_wrong_parameters_in_the_connection_string(instance_sql_defaults, connector, cs):
    instance_sql_defaults.update({'connector': connector, 'connection_string': cs + '=foo'})
    other_connector = 'odbc' if connector != 'odbc' else 'adodbapi'
    connection = Connection({}, instance_sql_defaults, None)
    match = (
        "%s has been provided in the connection string. "
        "This option is only available for %s connections, however %s has been selected"
        % (cs, other_connector, connector)
    )

    with pytest.raises(ConfigurationError, match=re.escape(match)):
        connection._connection_options_validation('somekey', 'somedb')


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_query_timeout(aggregator, dd_run_check, instance_docker):
    _run_test_query_timeout(aggregator, dd_run_check, instance_docker)


@windows_ci
@pytest.mark.integration
def test_query_timeout_windows(aggregator, dd_run_check, instance_sql_msoledb):
    _run_test_query_timeout(aggregator, dd_run_check, instance_sql_msoledb)


def _run_test_query_timeout(aggregator, dd_run_check, instance):
    instance['command_timeout'] = 1
    check = SQLServer(CHECK_NAME, {}, [instance])
    check.initialize_connection()
    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            # should complete quickly
            cursor.execute("select 1")
            assert cursor.fetchall(), "should have a result here"
            with pytest.raises(Exception) as e:
                cursor.execute("waitfor delay '00:00:02'")
                if isinstance(e, pyodbc.OperationalError):
                    assert 'timeout' in "".join(e.args).lower(), "must be a timeout"
                else:
                    import adodbapi

                    assert type(e) == adodbapi.apibase.DatabaseError
                    assert 'timeout' in "".join(e.args).lower(), "must be a timeout"


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connection_cleanup(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    # regular operation
    with check.connection.open_managed_default_connection():
        assert len(check.connection._conns) == 1
        with check.connection.get_managed_cursor() as cursor:
            cursor.execute("select 1")
            assert len(check.connection._conns) == 1
    assert len(check.connection._conns) == 0, "connection should have been closed"

    # db exception
    with pytest.raises(Exception) as e:
        with check.connection.open_managed_default_connection():
            assert len(check.connection._conns) == 1
            with check.connection.get_managed_cursor() as cursor:
                assert len(check.connection._conns) == 1
                cursor.execute("gimme some data")
    assert "incorrect syntax" in str(e).lower()
    assert len(check.connection._conns) == 0, "connection should have been closed"

    # application exception
    with pytest.raises(Exception) as e:
        with check.connection.open_managed_default_connection():
            assert len(check.connection._conns) == 1
            with check.connection.get_managed_cursor():
                assert len(check.connection._conns) == 1
                raise Exception("oops")
    assert "oops" in str(e)
    assert len(check.connection._conns) == 0, "connection should have been closed"
