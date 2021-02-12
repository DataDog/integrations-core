# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from datadog_checks.base import ConfigurationError

from datadog_checks.sqlserver.connection import Connection


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'connector, param',
     [
         pytest.param('adodbapi', 'adoprovider', id='Provider is ignored when using adodbapi'),
         pytest.param('odbc', 'dsn', id='DSN is ignored when using odbc'),
         pytest.param('odbc', 'driver', id='Driver is ignored when using odbc'),
     ]
)
def test_will_warn_parameters_for_the_wrong_connection(instance_sql2017_defaults, connector, param):
    instance_sql2017_defaults.update({
        'connector': connector,
        param: 'foo'
    })
    connection = Connection({}, instance_sql2017_defaults, None)
    connection.log = mock.MagicMock()
    connection._connection_options_validation('somekey', 'somedb')
    connection.log.warning.assert_called_once_with(
        "%s option will be ignored since %s connection is used", param, connector)


@pytest.mark.parametrize(
    'connector, cs, param',
     [
         pytest.param('adodbapi', 'DSN', 'dsn', id='Cannot define DSN twice'),
         pytest.param('adodbapi', 'DRIVER', 'driver', id='Cannot define DRIVER twice'),
         pytest.param('adodbapi', 'SERVER', 'host', id='Cannot define DRIVER twice'),
         pytest.param('adodbapi', 'UID', 'username', id='Cannot define UID twice'),
         pytest.param('adodbapi', 'PWD', 'password', id='Cannot define PWD twice'),
         pytest.param('odbc', 'PROVIDER', 'adoprovider', id='Cannot define PROVIDER twice'),
         pytest.param('odbc', 'Data Source', 'host', id='Cannot define Data source twice'),
         pytest.param('odbc', 'User ID', 'username', id='Cannot define User ID twice'),
         pytest.param('odbc', 'Password', 'password', id='Cannot define Password twice'),
     ]
)
def will_fail_for_duplicate_parameters(instance_sql2017_defaults, connector, cs, param):
    instance_sql2017_defaults.update({
        'connector': connector,
        param: 'foo',
        'connection_string': cs + "=foo"
    })
    connection = Connection({}, instance_sql2017_defaults, None)
    match = "%s has been provided both in the connection string and as a configuration option (%s), please specify it only once".format(cs, param)
    with pytest.raises(ConfigurationError, match=match):
        connection._connection_options_validation('somekey', 'somedb')


@pytest.mark.parametrize(
    'connector, cs, param',
     [
         pytest.param('odbc', 'DSN=foo', id='Cannot define DSN for odbc'),
         pytest.param('odbc', 'DRIVER=foo', id='Cannot define DRIVER for odbc'),
         pytest.param('odbc', 'SERVER=foo', id='Cannot define DRIVER for odbc'),
         pytest.param('odbc', 'UID=foo', id='Cannot define UID for odbc'),
         pytest.param('odbc', 'PWD=foo', id='Cannot define PWD for odbc'),
         pytest.param('adodbapi', 'PROVIDER=foo', id='Cannot define PROVIDER for adodbapi'),
         pytest.param('adodbapi', 'Data Source=foo', id='Cannot define Data source for adodbapi'),
         pytest.param('adodbapi', 'User ID=foo', id='Cannot define User ID for adodbapi'),
         pytest.param('adodbapi', 'Password=foo', id='Cannot define Password for adodbapi'),
     ]
)
def will_fail_for_wrong_parameters_in_the_connection_string(instance_sql2017_defaults, connector, cs):
    instance_sql2017_defaults.update({
        'connector': connector,
        'connection_string': cs
    })
    other_connector = 'odbc' if connector != 'odbc' else 'adodbapi'
    connection = Connection({}, instance_sql2017_defaults, None)
    match = "%s has been provided in the connection string. This option is only available for %s connections, however %s has been selected" % (cs, other_connector, connector)
    with pytest.raises(ConfigurationError, match=match):
        connection._connection_options_validation('somekey', 'somedb')