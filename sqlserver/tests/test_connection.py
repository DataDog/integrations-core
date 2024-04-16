# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

import mock
import pyodbc
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import running_on_windows_ci
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.connection import (
    SUPPORT_LINK,
    Connection,
    SQLConnectionError,
    parse_connection_string_properties,
)
from datadog_checks.sqlserver.connection_errors import ConnectionErrorCode, format_connection_exception

from .common import CHECK_NAME, SQLSERVER_MAJOR_VERSION


@pytest.mark.unit
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


@pytest.mark.unit
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
    check = SQLServer(CHECK_NAME, {}, [instance_minimal_defaults])
    connection = Connection(check.resolved_hostname, {}, instance_minimal_defaults, None)
    connection.log = mock.MagicMock()
    connection._connection_options_validation('somekey', 'somedb')
    if expect_warning:
        connection.log.warning.assert_called_once_with(
            "Username and password are ignored when using Windows authentication"
        )
    else:
        connection.log.warning.assert_not_called()


@pytest.mark.unit
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
    check = SQLServer(CHECK_NAME, {}, [instance_minimal_defaults])
    connection = Connection(check.resolved_hostname, {}, instance_minimal_defaults, None)
    connection.log = mock.MagicMock()
    connection._connection_options_validation('somekey', 'somedb')
    connection.log.warning.assert_called_once_with(
        "%s option will be ignored since %s connection is used", param, connector
    )


@pytest.mark.unit
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
    check = SQLServer(CHECK_NAME, {}, [instance_minimal_defaults])
    connection = Connection(check.resolved_hostname, {}, instance_minimal_defaults, None)
    if should_fail:
        match = (
            "%s has been provided both in the connection string and as a configuration option (%s), "
            "please specify it only once" % (cs, param)
        )

        with pytest.raises(ConfigurationError, match=re.escape(match)):
            connection._connection_options_validation('somekey', 'somedb')
    else:
        connection._connection_options_validation('somekey', 'somedb')


@pytest.mark.unit
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
    check = SQLServer(CHECK_NAME, {}, [instance_minimal_defaults])
    connection = Connection(check.resolved_hostname, {}, instance_minimal_defaults, None)
    match = (
        "%s has been provided in the connection string. "
        "This option is only available for %s connections, however %s has been selected"
        % (cs, other_connector, connector)
    )

    with pytest.raises(ConfigurationError, match=re.escape(match)):
        connection._connection_options_validation('somekey', 'somedb')


@pytest.mark.unit
@pytest.mark.parametrize(
    "name,managed_identity_config,should_fail,expected_err",
    [
        (
            "valid managed_identity configuration",
            {
                'managed_identity': {
                    'client_id': "foo",
                },
            },
            False,
            None,
        ),
        (
            "valid config, but username/password set raises ConfigurationError",
            {
                'managed_identity': {
                    'client_id': 'foo',
                },
                "username": "foo",
                "password": "shame-nun",
            },
            True,
            (
                "Azure AD Authentication is configured, but username and password properties are also set "
                "please remove `username` and `password` from your instance config to use"
                "AD Authentication with a Managed Identity"
            ),
        ),
        (
            "managed_identity without client_id set raises ConfigurationError",
            {
                'managed_identity': {
                    'not_what_i_want': 'foo',
                },
            },
            True,
            (
                "Azure Managed Identity Authentication is not properly configured "
                "missing required property, client_id"
            ),
        ),
    ],
)
def test_managed_auth_config_valid(instance_minimal_defaults, name, managed_identity_config, should_fail, expected_err):
    instance_minimal_defaults.pop('username')
    instance_minimal_defaults.pop('password')
    if managed_identity_config:
        for k, v in managed_identity_config.items():
            instance_minimal_defaults[k] = v
    instance_minimal_defaults.update({'connector': 'odbc'})
    check = SQLServer(CHECK_NAME, {}, [instance_minimal_defaults])
    connection = Connection(check.resolved_hostname, {}, instance_minimal_defaults, None)
    if should_fail:
        with pytest.raises(ConfigurationError, match=re.escape(expected_err)):
            connection._connection_options_validation('somekey', 'somedb')
    else:
        connection._connection_options_validation('somekey', 'somedb')


@pytest.mark.unit
@pytest.mark.parametrize(
    'host, port, expected_host',
    [
        pytest.param(
            '1.2.3.4', 22, '1.2.3.4,22', id='if port provided as a config option as an int, it should be recognized'
        ),
        pytest.param(
            '1.2.3.4', '22', '1.2.3.4,22', id='if port provided as a config option as a string, it should be recognized'
        ),
        pytest.param('1.2.3.4', 'mcnugget', '1.2.3.4,1433', id='if port is not numeric, it should use default port'),
        pytest.param(
            '1.2.3.4,mcnugget',
            None,
            '1.2.3.4,1433',
            id='if host port is not numeric, it should use default port',
        ),
        pytest.param(
            '1.2.3.4,22',
            None,
            '1.2.3.4,22',
            id='if port is provided as part of host, it should be recognized',
        ),
        pytest.param(
            '1.2.3.4',
            None,
            '1.2.3.4,1433',
            id='if no port is provided anywhere, should default to 1433',
        ),
        pytest.param(
            '1.2.3.4,35',
            22,
            '1.2.3.4,35',
            id='if port is provided and included in host string, host port is used',
        ),
        pytest.param(
            '1.2.3.4,0',
            None,
            '1.2.3.4',
            id='if port provided in host string is 0, return a string with only host',
        ),
        pytest.param(
            '1.2.3.4',
            0,
            '1.2.3.4',
            id='if port provided via port config option is 0, return a string with only host',
        ),
    ],
)
def test_config_with_and_without_port(instance_minimal_defaults, host, port, expected_host):
    instance_minimal_defaults["host"] = host
    instance_minimal_defaults["port"] = port
    check = SQLServer(CHECK_NAME, {}, [instance_minimal_defaults])
    connection = Connection(check.resolved_hostname, {}, instance_minimal_defaults, None)
    _, result_host, _, _, _, _ = connection._get_access_info('somekey', 'somedb')
    assert result_host == expected_host


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.skipif(running_on_windows_ci() and SQLSERVER_MAJOR_VERSION == 2019, reason='Test flakes on this set up')
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
    assert "incorrect syn" in str(e).lower()
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
    instance_docker['procedure_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    instance_docker['query_activity'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    instance_docker['collect_settings'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    check = SQLServer(CHECK_NAME, {}, [instance_docker])

    dd_run_check(check)
    aggregator.assert_service_check(
        'sqlserver.can_connect',
        status=check.OK,
    )
    aggregator.reset()

    try:
        # Break the connection
        check.connection = Connection(
            check.resolved_hostname, {}, {'host': '', 'username': '', 'password': ''}, check.handle_service_check
        )
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


@pytest.mark.unit
@pytest.mark.parametrize(
    "test_case_name,instance_overrides,expected_error_patterns,expected_error",
    [
        (
            "unknown_adoprovider",
            {'adoprovider': "fake"},
            {".*": "TCP-connection\\(OK\\).*Provider cannot be found. It may not be properly installed."},
            ConnectionErrorCode.driver_not_found,
        ),
        (
            "unknown_odbc_driver",
            {'driver': "{SQL Driver For Fake Tests 2022}"},
            {
                "odbc-linux": "TCP-connection\\(OK\\).*"
                "Can't open lib .* file not found .* configured odbc driver .* not in list of installed drivers",
                "odbc-windows": "TCP-connection\\(OK\\).*"
                "Data source name not found.* and no default driver specified",
            },
            ConnectionErrorCode.driver_not_found,
        ),
        (
            "odbc_driver_incorrect_dsn",
            {'dsn': "Not The Real DSN"},
            {
                "odbc-linux|odbc-windows": "TCP-connection\\(OK\\).*"
                "Data source name not found.* and no default driver specified",
            },
            ConnectionErrorCode.driver_not_found,
        ),
        (
            "unknown_hostname",
            {"host": "wrong"},
            {
                "odbc-windows|MSOLEDBSQL": "TCP-connection\\(ERROR: getaddrinfo failed\\).*"
                "TCP Provider: No such host is known",
                "SQLOLEDB|SQLNCLI11": "TCP-connection\\(ERROR: getaddrinfo failed\\).*"
                "could not open database requested by login",
                "odbc-linux": "((TCP-connection\\(ERROR: Temporary failure in name resolution\\).*)*"
                "Unable to connect to |"
                "TCP-connection\\(ERROR: Name or service not known\\).*Login timeout expired)",
            },
            ConnectionErrorCode.tcp_connection_failed,
        ),
        (
            "failed_tcp_connection",
            {"host": "localhost,9999"},
            {
                "odbc-windows|MSOLEDBSQL": "TCP Provider: No connection could be made"
                " because the target machine actively refused it",
                "SQLOLEDB|SQLNCLI11": "TCP-connection\\(ERROR: No connection could be made "
                "because the target machine actively refused it\\).*"
                "could not open database requested by login",
                "odbc-linux": "TCP-connection\\(ERROR: Connection refused\\).*"
                "(Unable to connect: Adaptive Server is unavailable|Login timeout expired*)",
            },
            ConnectionErrorCode.tcp_connection_failed,
        ),
        (
            "unknown_database",
            {"database": "wrong"},
            {
                "odbc-windows|MSOLEDBSQL": "TCP-connection\\(OK\\).*Cannot open database .* requested by the login.",
                "SQLOLEDB|SQLNCLI11": "TCP-connection\\(OK\\).*could not open database requested by login",
                "odbc-linux": "TCP-connection\\(OK\\).*"
                "(Cannot open database .* requested by the login|Login failed for user)",
            },
            ConnectionErrorCode.tcp_connection_failed,
        ),
        (
            "invalid_credentials",
            {"username": "wrong"},
            {
                "odbc-windows|odbc-linux|MSOLEDBSQL": "TCP-connection\\(OK\\).*Login failed for user",
                "SQLOLEDB|SQLNCLI11": "TCP-connection\\(OK\\).*login failed for user",
            },
            ConnectionErrorCode.login_failed_for_user,
        ),
    ],
)
def test_connection_error_reporting(
    test_case_name,
    instance_docker,
    instance_overrides,
    expected_error_patterns,
    expected_error,
):
    for key, value in instance_overrides.items():
        instance_docker[key] = value
    if 'adoprovider' in instance_overrides:
        if instance_docker['connector'] == 'odbc':
            pytest.skip("adoprovider_override is not relevant for the odbc connector")
        adoprovider_override = instance_overrides['adoprovider'].upper()
        if adoprovider_override not in Connection.VALID_ADOPROVIDERS:
            Connection.VALID_ADOPROVIDERS.append(adoprovider_override)
    if 'adoprovider' in instance_docker and ('driver' in instance_overrides or 'dsn' in instance_overrides):
        pytest.skip("driver or DSN overrides is not relevant for the adoprovider")

    driver = "odbc" if instance_docker['connector'] == "odbc" else instance_docker['adoprovider']
    if driver == "odbc":
        # add OS suffix as the linux ODBC driver has different error messages from the windows one
        driver = driver + "-" + ("windows" if "WINDOWS_SQLSERVER_DRIVER" in os.environ else "linux")
    matching_patterns = [p for driver_pattern, p in expected_error_patterns.items() if re.match(driver_pattern, driver)]
    assert len(matching_patterns) == 1, "there must be exactly one matching driver pattern"
    expected_error_pattern = matching_patterns[0]

    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    connection = Connection(check.resolved_hostname, check.init_config, check.instance, check.handle_service_check)
    with pytest.raises(SQLConnectionError) as excinfo:
        with connection.open_managed_default_connection():
            pytest.fail("connection should not have succeeded")

    message = str(excinfo.value).lower()
    assert re.search(expected_error_pattern, message, re.IGNORECASE)
    expected_link = "see {}#{} for more details".format(SUPPORT_LINK, expected_error.value)
    if expected_error == ConnectionErrorCode.tcp_connection_failed:
        user_link = "see {}#{} for more details".format(SUPPORT_LINK, ConnectionErrorCode.login_failed_for_user.value)
        assert expected_link.lower() in message or user_link.lower() in message
    else:
        assert expected_link.lower() in message


@pytest.mark.unit
@pytest.mark.parametrize(
    "error_message,expected_error",
    [
        (
            "OperationalError('08001', '[08001] "
            "[Microsoft][ODBC SQL Server Driver][DBNETLIB]SSL Security error (18) "
            "(SQLDriverConnect); [08001] [Microsoft][ODBC SQL Server Driver][DBNETLIB]ConnectionOpen "
            "(SECCreateCredentials()). (1); [08001] "
            "[Microsoft][ODBC SQL Server Driver]Invalid connection string attribute (0)')",
            ConnectionErrorCode.ssl_security_error,
        ),
        (
            "OperationalError(com_error(-2147352567, 'Exception occurred.', "
            "(0, 'Microsoft OLE DB Driver 19 for SQL Server', "
            "'SSL Provider: The certificate chain was issued by an authority that is not trusted.\\r\\n', "
            "None, 0, -2147467259), None)",
            ConnectionErrorCode.certificate_verify_failed,
        ),
        (
            "InterfaceError('IM002', '[IM002] [Microsoft][ODBC Driver Manager] "
            "Data source name not found and no default driver specified (0) (SQLDriverConnect)')",
            ConnectionErrorCode.driver_not_found,
        ),
        (
            "OperationalError(com_error(-2147352567, 'Exception occurred.', (0, 'Microsoft OLE DB Driver 19 "
            "for SQL Server', 'Login failed. The login is from an untrusted domain and cannot be used with "
            "Windows authentication.', None, 0, -2147467259), None)",
            ConnectionErrorCode.login_failed_for_user,
        ),
        (
            "OperationalError(com_error(-2147352567, 'Exception occurred.', (0, 'Microsoft OLE DB Driver 19 "
            "for SQL Server', 'I can't say why I couldn't connect!', None, 0, -2147467259), None)",
            ConnectionErrorCode.unknown,
        ),
    ],
)
def test_format_connection_error(
    instance_docker,
    error_message,
    expected_error,
):
    driver = "odbc" if instance_docker['connector'] == "odbc" else instance_docker['adoprovider']
    _, conn_err = format_connection_exception(error_message, driver)
    assert conn_err
    assert conn_err.value == expected_error.value


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_restore_current_database_context(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()
    with check.connection.open_managed_default_connection():
        current_db = check.connection._get_current_database_context()
        with check.connection.restore_current_database_context():
            with check.connection.get_managed_cursor() as cursor:
                cursor.execute("USE tempdb")
                assert check.connection._get_current_database_context() == "tempdb"
        assert check.connection._get_current_database_context() == current_db
