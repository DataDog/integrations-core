# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.sqlserver import SQLConnectionError

# mark the whole module
pytestmark = pytest.mark.unit

CHECK_NAME = 'sqlserver'


def test_get_cursor(instance_sql2008):
    """
    Ensure we don't leak connection info in case of a KeyError when the
    connection pool is empty or the params for `get_cursor` are invalid.
    """
    check = SQLServer(CHECK_NAME, {}, {}, [])
    with pytest.raises(SQLConnectionError):
        check.get_cursor(instance_sql2008, 'foo')
