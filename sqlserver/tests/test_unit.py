# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

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


def test_get_cursor(instance_sql2017):
    """
    Ensure we don't leak connection info in case of a KeyError when the
    connection pool is empty or the params for `get_cursor` are invalid.
    """
    check = SQLServer(CHECK_NAME, {}, [instance_sql2017])
    with pytest.raises(SQLConnectionError):
        check.connection.get_cursor('foo')


def test_missing_db(instance_sql2017):
    instance = copy.copy(instance_sql2017)
    instance['ignore_missing_database'] = False
    with mock.patch('datadog_checks.sqlserver.connection.Connection.check_database', return_value=(False, 'db')):
        with pytest.raises(ConfigurationError):
            check = SQLServer(CHECK_NAME, {}, [instance])

    instance['ignore_missing_database'] = True
    with mock.patch('datadog_checks.sqlserver.connection.Connection.check_database', return_value=(False, 'db')):
        check = SQLServer(CHECK_NAME, {}, [instance])
        assert check.do_check is False

# FCI metrics will not appear in `compose` or `compose-ha`,
# so this test ensures that the metric is still checked.
# def test_fci_metrics(instance_sql2017):
#     instance = copy.copy(instance_sql2017)
#     instance['include_fci_metrics'] = True


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
def test_check_local(aggregator, init_config, instance_sql2017):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_sql2017])
    sqlserver_check.check(instance_sql2017)
    expected_tags = instance_sql2017.get('tags', []) + ['host:{}'.format(LOCAL_SERVER), 'db:master']
    assert_metrics(aggregator, expected_tags)


@windows_ci
@pytest.mark.parametrize('adoprovider', ['SQLOLEDB', 'SQLNCLI11'])
def test_check_adoprovider(aggregator, init_config, instance_sql2017, adoprovider):
    instance = copy.deepcopy(instance_sql2017)
    instance['adoprovider'] = adoprovider

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance])
    sqlserver_check.check(instance)
    expected_tags = instance.get('tags', []) + ['host:{}'.format(LOCAL_SERVER), 'db:master']
    assert_metrics(aggregator, expected_tags)
