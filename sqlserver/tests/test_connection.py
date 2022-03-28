#!/usr/bin/python
# -*- coding: utf8 -*-
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import mock
import pyodbc
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.connection import Connection, parse_connection_string_properties

from .common import CHECK_NAME

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'cs,parsed',
    [
        pytest.param(
            'HOST=foo;password={πA s";{}}w0rd};',
            {"HOST": "foo", "password": 'πA s";{}w0rd'},
            id="closing bracket escape sequence",
        ),
        pytest.param(
            'host=foo;password={πass";{}}word}',
            {"host": "foo", "password": 'πass";{}word'},
            id="final semicolon is optional",
        ),
        pytest.param('A=B; C=D', {"A": "B", "C": 'D'}, id="spaces after semicolons are ignored"),
        pytest.param('A B=C;', {"A B": "C"}, id="spaces allowed inside a key"),
        pytest.param('A=B C;', {"A": "B C"}, id="spaces allowed inside a value"),
        pytest.param('A=C ;', {"A": "C "}, id="spaces allowed after a value"),
        pytest.param('A=B ;C=D', {"A": "B ", "C": 'D'}, id="spaces allowed after a value, they become part of it"),
        pytest.param('host=foo;password={pass";{}word}', None, id="escape too early then invalid character"),
        pytest.param('host=foo;password={incomplete_escape;', None, id="incomplete escape"),
        pytest.param('host=foo;password=;', None, id="empty value"),
        pytest.param('host=foo;=hello;', None, id="empty key"),
        pytest.param('host=foo;;', None, id="empty both"),
        pytest.param('host==foo;', None, id="double equal"),
    ],
)
def test_parse_connection_string_properties(cs, parsed):
    if parsed:
        assert parse_connection_string_properties(cs) == parsed
        return
    with pytest.raises(ConfigurationError):
        parse_connection_string_properties(cs)


@pytest.mark.parametrize(
    'cs,username,password,expect_warning',
    [
        pytest.param('host=A;Trusted_Connection=true', "bob", "password123", True),
        pytest.param('host=A;Trusted_Connection=true', None, None, False),
        pytest.param('host=A;', "bob", "password123", False),
    ],
)
def test_warn_trusted_connection_username_pass(instance_minimal_defaults, cs, username, password, expect_warning):
    instance_minimal_defaults["connection_string"] = cs
    instance_minimal_defaults["username"] = username
    instance_minimal_defaults["password"] = password
    connection = Connection({}, instance_minimal_defaults, None)
    connection.log = mock.MagicMock()
    connection._connection_options_validation('somekey', 'somedb')
    if expect_warning:
        connection.log.warning.assert_called_once_with(
            "Username and password are ignored when using Windows authentication"
        )
    else:
        connection.log.warning.assert_not_called()


@pytest.mark.parametrize(
    'connector, param',
    [
        pytest.param('odbc', 'adoprovider', id='Provider is ignored when using odbc'),
        pytest.param('adodbapi', 'dsn', id='DSN is ignored when using adodbapi'),
        pytest.param('adodbapi', 'driver', id='Driver is ignored when using adodbapi'),
    ],
)
def test_will_warn_parameters_for_the_wrong_connection(instance_minimal_defaults, connector, param):
    instance_minimal_defaults.update({'connector': connector, param: 'foo'})
    connection = Connection({}, instance_minimal_defaults, None)
    connection.log = mock.MagicMock()
    connection._connection_options_validation('somekey', 'somedb')
    connection.log.warning.assert_called_once_with(
        "%s option will be ignored since %s connection is used", param, connector
    )


@pytest.mark.parametrize(
    'connector, cs, param, should_fail',
    [
        pytest.param('odbc', 'DSN', 'dsn', True, id='Cannot define DSN twice'),
        pytest.param('odbc', 'DRIVER', 'driver', True, id='Cannot define DRIVER twice'),
        pytest.param('odbc', 'SERVER', 'host', True, id='Cannot define DRIVER twice'),
        pytest.param('odbc', 'UID', 'username', True, id='Cannot define UID twice'),
        pytest.param('odbc', 'PWD', 'password', True, id='Cannot define PWD twice'),
        pytest.param(
            'odbc',
            'TrustServerCertificate',
            None,
            False,
            id='Should not fail as this option is not configurable in the base instance.',
        ),
        pytest.param('adodbapi', 'PROVIDER', 'adoprovider', True, id='Cannot define PROVIDER twice'),
        pytest.param('adodbapi', 'Data Source', 'host', True, id='Cannot define Data Source twice'),
        pytest.param('adodbapi', 'User ID', 'username', True, id='Cannot define User ID twice'),
        pytest.param('adodbapi', 'Password', 'password', True, id='Cannot define Password twice'),
    ],
)
def test_will_fail_for_duplicate_parameters(instance_minimal_defaults, connector, cs, param, should_fail):
    instance_minimal_defaults.update({'connector': connector, param: 'foo', 'connection_string': cs + "=foo"})
    connection = Connection({}, instance_minimal_defaults, None)
    if should_fail:
        match = (
            "%s has been provided both in the connection string and as a configuration option (%s), "
            "please specify it only once" % (cs, param)
        )

        with pytest.raises(ConfigurationError, match=re.escape(match)):
            connection._connection_options_validation('somekey', 'somedb')
    else:
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
def test_will_fail_for_wrong_parameters_in_the_connection_string(instance_minimal_defaults, connector, cs):
    instance_minimal_defaults.update({'connector': connector, 'connection_string': cs + '=foo'})
    other_connector = 'odbc' if connector != 'odbc' else 'adodbapi'
    connection = Connection({}, instance_minimal_defaults, None)
    match = (
        "%s has been provided in the connection string. "
        "This option is only available for %s connections, however %s has been selected"
        % (cs, other_connector, connector)
    )

    with pytest.raises(ConfigurationError, match=re.escape(match)):
        connection._connection_options_validation('somekey', 'somedb')


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_query_timeout(instance_docker):
    instance_docker['command_timeout'] = 1
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
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


@pytest.mark.integration
def test_connection_failure(aggregator, dd_run_check, instance_docker):
    instance_docker['dbm'] = True
    instance_docker['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    instance_docker['query_activity'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    check = SQLServer(CHECK_NAME, {}, [instance_docker])

    dd_run_check(check)
    aggregator.assert_service_check(
        'sqlserver.can_connect',
        status=check.OK,
    )
    aggregator.reset()

    try:
        # Break the connection
        check.connection = Connection({}, {'host': '', 'username': '', 'password': ''}, check.handle_service_check)
        dd_run_check(check)
    except Exception:
        aggregator.assert_service_check(
            'sqlserver.can_connect',
            status=check.CRITICAL,
        )
        aggregator.reset()

    check.initialize_connection()
    dd_run_check(check)
    aggregator.assert_service_check(
        'sqlserver.can_connect',
        status=check.OK,
    )
