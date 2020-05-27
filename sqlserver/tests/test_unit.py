# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import EnvVars
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.sqlserver import SQLConnectionError
from datadog_checks.sqlserver.utils import set_default_driver_conf

# mark the whole module
pytestmark = pytest.mark.unit

CHECK_NAME = 'sqlserver'


def test_get_cursor(instance_sql2017):
    """
    Ensure we don't leak connection info in case of a KeyError when the
    connection pool is empty or the params for `get_cursor` are invalid.
    """
    check = SQLServer(CHECK_NAME, {}, [])
    with pytest.raises(SQLConnectionError):
        check.get_cursor(instance_sql2017, 'foo')


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
