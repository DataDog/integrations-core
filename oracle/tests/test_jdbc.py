# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

import mock

from datadog_checks.oracle import Oracle

from .common import CHECK_NAME, mock_bad_executor


@pytest.mark.parametrize(
    "instance, expected_tags, dsn, jdbc_connect_properties",
    [
        # TCP
        (
            {
                'server': 'localhost:1521',
                'username': 'system',
                'password': 'oracle',
                'service_name': 'xe',
                'protocol': 'TCP',
                'tags': ['optional:tag1'],
                'loader': 'python',
            },
            ['server:localhost:1521', 'optional:tag1'],
            "//localhost:1521/xe",
            {'user': 'system', 'password': 'oracle'},
        ),
        # TCPS
        (
            {
                'server': 'localhost:2484',
                'username': 'system',
                'password': 'oracle',
                'service_name': 'xe',
                'protocol': 'TCPS',
                'tags': ['optional:tag1'],
                'loader': 'python',
            },
            ['server:localhost:2484', 'optional:tag1'],
            "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=localhost)(PORT=2484))(CONNECT_DATA=(SERVICE_NAME=xe)))",
            {
                'user': 'system',
                'password': 'oracle',
                'javax.net.ssl.trustStoreType': None,
                'javax.net.ssl.trustStorePassword': '',
                'javax.net.ssl.trustStore': None,
            },
        ),
    ],
)
def test__get_connection_jdbc(instance, dd_run_check, aggregator, expected_tags, dsn, jdbc_connect_properties):
    """
    Test the _get_connection method using the JDBC client
    """
    check = Oracle(CHECK_NAME, {}, [instance])
    check.can_use_jdbc = mock.Mock(return_value=True)

    con = mock.MagicMock()

    jdb = mock.MagicMock()
    jdb.connect.return_value = con
    jpype = mock.MagicMock(isJVMStarted=lambda: False)

    mocks = [
        ('datadog_checks.oracle.oracle.jdb', jdb),
        ('datadog_checks.oracle.oracle.jpype', jpype),
        ('datadog_checks.oracle.oracle.JDBC_IMPORT_ERROR', None),
    ]
    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))
        dd_run_check(check)
        assert check._cached_connection == con

    jdb.connect.assert_called_with(
        'oracle.jdbc.OracleDriver', "jdbc:oracle:thin:@" + dsn, jdbc_connect_properties, None
    )
    aggregator.assert_service_check("oracle.can_connect", check.OK, count=1, tags=expected_tags)
    aggregator.assert_service_check("oracle.can_query", check.OK, count=1, tags=expected_tags)


def test__get_connection_jdbc_query_fail(check, dd_run_check, aggregator):
    """
    Test the _get_connection method using the JDBC client and unsuccessfully query DB
    """
    check.can_use_jdbc = mock.Mock(return_value=True)
    con = mock.MagicMock()
    expected_tags = ['server:localhost:1521', 'optional:tag1']

    check._query_manager.executor = mock_bad_executor()

    jdb = mock.MagicMock()
    jdb.connect.return_value = con
    jpype = mock.MagicMock(isJVMStarted=lambda: False)

    check._query_errors = 1

    mocks = [
        ('datadog_checks.oracle.oracle.jdb', jdb),
        ('datadog_checks.oracle.oracle.jpype', jpype),
        ('datadog_checks.oracle.oracle.JDBC_IMPORT_ERROR', None),
    ]
    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))
        dd_run_check(check)

    aggregator.assert_service_check("oracle.can_connect", check.OK, count=1, tags=expected_tags)
    aggregator.assert_service_check("oracle.can_query", check.CRITICAL, count=1, tags=expected_tags)
