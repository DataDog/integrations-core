# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import mock
import pytest

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from datadog_checks.teradata.check import TeradataCheck

from .common import CHECK_NAME


@pytest.mark.parametrize(
    "test_instance, expected_tags, conn_params",
    [
        pytest.param(
            {
                'server': 'localhost',
                'username': 'datadog',
                'password': 'dd_teradata',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            {
                "host": "localhost",
                "account": None,
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": None,
                "logdata": None,
                "user": "datadog",
                "password": "dd_teradata",
                "https_port": "443",
                "sslca": None,
                "sslcapath": None,
                "sslmode": "PREFER",
                "sslprotocol": "TLSv1.2",
            },
            id="Use default options",
        ),
        pytest.param(
            {
                'server': 'td-internal',
                'port': 1125,
                'username': 'dd',
                'password': 'td_datadog',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:td-internal:1125'],
            {
                "host": "td-internal",
                "account": None,
                "database": "AdventureWorksDW",
                "dbs_port": "1125",
                "logmech": None,
                "logdata": None,
                "user": "dd",
                "password": "td_datadog",
                "https_port": "443",
                "sslca": None,
                "sslcapath": None,
                "sslmode": "PREFER",
                "sslprotocol": "TLSv1.2",
            },
            id="Use custom server, db port, and driver path",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'username': 'dd',
                'password': 'td_datadog',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            {
                "host": "localhost",
                "account": None,
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": None,
                "logdata": None,
                "user": "dd",
                "password": "td_datadog",
                "https_port": "443",
                "sslca": None,
                "sslcapath": None,
                "sslmode": "PREFER",
                "sslprotocol": "TLSv1.2",
            },
            id="Use default TLS options",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'https_port': 543,
                'ssl_mode': 'REQUIRE',
                'username': 'dd',
                'password': 'td_datadog',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            {
                "host": "localhost",
                "account": None,
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": None,
                "logdata": None,
                "user": "dd",
                "password": "td_datadog",
                "https_port": "543",
                "sslca": None,
                "sslcapath": None,
                "sslmode": "REQUIRE",
                "sslprotocol": "TLSv1.2",
            },
            id="Use custom TLS options",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'auth_mechanism': 'JWT',
                'auth_data': 'token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4g'
                'RG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            {
                "host": "localhost",
                "account": None,
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "JWT",
                "logdata": "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9"
                "lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "user": None,
                "password": None,
                "https_port": "443",
                "sslca": None,
                "sslcapath": None,
                "sslmode": "PREFER",
                "sslprotocol": "TLSv1.2",
            },
            id="Use JWT auth option",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'auth_mechanism': 'KRB5',
                'auth_data': 'dd@localhost@@td_datadog',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            {
                "host": "localhost",
                "account": None,
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "KRB5",
                "logdata": "dd@localhost@@td_datadog",
                "user": None,
                "password": None,
                "https_port": "443",
                "sslca": None,
                "sslcapath": None,
                "sslmode": "PREFER",
                "sslprotocol": "TLSv1.2",
            },
            id="Use KRB5 auth option",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'auth_mechanism': 'LDAP',
                'auth_data': 'dd@@td_datadog',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            {
                "host": "localhost",
                "account": None,
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "LDAP",
                "logdata": "dd@@td_datadog",
                "user": None,
                "password": None,
                "https_port": "443",
                "sslca": None,
                "sslcapath": None,
                "sslmode": "PREFER",
                "sslprotocol": "TLSv1.2",
            },
            id="Use LDAP auth option",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'auth_mechanism': 'TDNEGO',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            {
                "host": "localhost",
                "account": None,
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "TDNEGO",
                "logdata": None,
                "user": None,
                "password": None,
                "https_port": "443",
                "sslca": None,
                "sslcapath": None,
                "sslmode": "PREFER",
                "sslprotocol": "TLSv1.2",
            },
            id="Use TDNEGO auth option",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'username': 'datadog',
                'password': 'dd_teradata',
                'auth_mechanism': 'TD2',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            {
                "host": "localhost",
                "account": None,
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "TD2",
                "logdata": None,
                "user": "datadog",
                "password": "dd_teradata",
                "https_port": "443",
                "sslca": None,
                "sslcapath": None,
                "sslmode": "PREFER",
                "sslprotocol": "TLSv1.2",
            },
            id="Use TD2 auth option (default)",
        ),
    ],
)
def test__connect(test_instance, dd_run_check, aggregator, expected_tags, conn_params):
    """
    Test the _connect method
    """
    check = TeradataCheck(CHECK_NAME, {}, [test_instance])
    conn = mock.MagicMock()

    teradatasql = mock.MagicMock()
    teradatasql.connect.return_value = conn

    mocks = [
        ('datadog_checks.teradata.check.teradatasql', teradatasql),
        ('datadog_checks.teradata.check.TERADATASQL_IMPORT_ERROR', None),
    ]

    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))
        dd_run_check(check)
        assert check._connection == conn

    teradatasql.connect.assert_called_with(json.dumps(conn_params))
    aggregator.assert_service_check("teradata.can_connect", check.OK, tags=expected_tags)
