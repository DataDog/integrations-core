# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from datadog_checks.teradata.check import TeradataCheck

from .common import CHECK_NAME


@pytest.mark.parametrize(
    "test_instance, expected_tags, jdbc_conn_str, jdbc_connect_properties, jdbc_driver_path",
    [
        pytest.param(
            {
                'server': 'localhost',
                'username': 'datadog',
                'password': 'dd_teradata',
                'jdbc_driver_path': '/terajdbc4.jar',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            'jdbc:teradata://localhost/dbs_port=1025,https_port=443,sslmode=PREFER,sslprotocol=TLSv1.2',
            {'user': 'datadog', 'password': 'dd_teradata'},
            '/terajdbc4.jar',
            id="Use default options",
        ),
        pytest.param(
            {
                'server': 'td-internal',
                'port': 1125,
                'username': 'dd',
                'password': 'td_datadog',
                'jdbc_driver_path': '/jre/lib/ext/terajdbc4.jar',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:td-internal:1125'],
            'jdbc:teradata://td-internal/dbs_port=1125,https_port=443,sslmode=PREFER,sslprotocol=TLSv1.2',
            {'user': 'dd', 'password': 'td_datadog'},
            '/jre/lib/ext/terajdbc4.jar',
            id="Use custom server, db port, and driver path",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'use_tls': True,
                'username': 'dd',
                'password': 'td_datadog',
                'jdbc_driver_path': '/terajdbc4.jar',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            'jdbc:teradata://localhost/dbs_port=1025,https_port=443,sslmode=PREFER,sslprotocol=TLSv1.2',
            {'user': 'dd', 'password': 'td_datadog'},
            '/terajdbc4.jar',
            id="Use default TLS options",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'use_tls': True,
                'https_port': 543,
                'ssl_mode': 'REQUIRE',
                'username': 'dd',
                'password': 'td_datadog',
                'jdbc_driver_path': '/terajdbc4.jar',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            'jdbc:teradata://localhost/dbs_port=1025,https_port=543,sslmode=REQUIRE,sslprotocol=TLSv1.2',
            {'user': 'dd', 'password': 'td_datadog'},
            '/terajdbc4.jar',
            id="Use custom TLS options",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'auth_mechanism': 'JWT',
                'auth_data': 'token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4g'
                'RG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
                'jdbc_driver_path': '/terajdbc4.jar',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            'jdbc:teradata://localhost/dbs_port=1025,https_port=443,logdata=token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
            'eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6'
            'yJV_adQssw5c,logmech=JWT,sslmode=PREFER,sslprotocol=TLSv1.2',
            {},
            '/terajdbc4.jar',
            id="Use JWT auth option",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'auth_mechanism': 'KRB5',
                'auth_data': 'dd@localhost@@td_datadog',
                'jdbc_driver_path': '/terajdbc4.jar',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            'jdbc:teradata://localhost/dbs_port=1025,https_port=443,logdata=dd@localhost@@td_datadog,logmech=KRB5,'
            'sslmode=PREFER,sslprotocol=TLSv1.2',
            {},
            '/terajdbc4.jar',
            id="Use KRB5 auth option",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'auth_mechanism': 'LDAP',
                'auth_data': 'dd@@td_datadog',
                'jdbc_driver_path': '/terajdbc4.jar',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            'jdbc:teradata://localhost/dbs_port=1025,https_port=443,logdata=dd@@td_datadog,logmech=LDAP,'
            'sslmode=PREFER,sslprotocol=TLSv1.2',
            {},
            '/terajdbc4.jar',
            id="Use LDAP auth option",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'auth_mechanism': 'TDNEGO',
                'jdbc_driver_path': '/terajdbc4.jar',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            'jdbc:teradata://localhost/dbs_port=1025,https_port=443,logmech=TDNEGO,'
            'sslmode=PREFER,sslprotocol=TLSv1.2',
            {},
            '/terajdbc4.jar',
            id="Use TDNEGO auth option",
        ),
        pytest.param(
            {
                'server': 'localhost',
                'username': 'datadog',
                'password': 'dd_teradata',
                'auth_mechanism': 'TD2',
                'jdbc_driver_path': '/terajdbc4.jar',
                'database': 'AdventureWorksDW',
            },
            ['teradata_server:localhost:1025'],
            'jdbc:teradata://localhost/dbs_port=1025,https_port=443,logmech=TD2,sslmode=PREFER,sslprotocol=TLSv1.2',
            {'user': 'datadog', 'password': 'dd_teradata'},
            '/terajdbc4.jar',
            id="Use TD2 auth option (default)",
        ),
    ],
)
def test__connect(
    test_instance, dd_run_check, aggregator, expected_tags, jdbc_conn_str, jdbc_connect_properties, jdbc_driver_path
):
    """
    Test the _connect method using the JDBC client
    """
    check = TeradataCheck(CHECK_NAME, {}, [test_instance])
    conn = mock.MagicMock()

    jdb = mock.MagicMock()
    jdb.connect.return_value = conn
    jpype = mock.MagicMock(isJVMStarted=lambda: False)

    mocks = [
        ('datadog_checks.teradata.check.jdb', jdb),
        ('datadog_checks.teradata.check.jpype', jpype),
        ('datadog_checks.teradata.check.JDBC_IMPORT_ERROR', None),
    ]

    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))
        dd_run_check(check)
        assert check._connection == conn

    jdb.connect.assert_called_with(
        'com.teradata.jdbc.TeraDriver',
        jdbc_conn_str,
        jdbc_connect_properties,
        jdbc_driver_path,
    )
    aggregator.assert_service_check("teradata.can_connect", check.OK, tags=expected_tags)
