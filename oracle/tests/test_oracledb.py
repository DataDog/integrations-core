# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.oracle import Oracle

from .common import CHECK_NAME, mock_bad_executor


@pytest.mark.parametrize(
    "instance, expected_tags",
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
        ),
    ],
)
def test__get_connection_oracledb(instance, dd_run_check, aggregator, expected_tags):
    """
    Test the _get_connection method using the instant client
    """
    check = Oracle(CHECK_NAME, {}, [instance])
    con = mock.MagicMock()
    with mock.patch('datadog_checks.oracle.oracle.oracledb') as pyoradb:
        pyoradb.connect.return_value = con
        dd_run_check(check)
        assert check._cached_connection == con
        pyoradb.connect.assert_called_with(user='system', password='oracle', dsn=check._get_dsn())
        aggregator.assert_service_check("oracle.can_connect", check.OK, count=1, tags=expected_tags)
        aggregator.assert_service_check("oracle.can_query", check.OK, count=1, tags=expected_tags)


@pytest.mark.parametrize(
    "instance, expected_tags",
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
        ),
    ],
)
def test__get_connection_oracledb_instant_client(instance, dd_run_check, aggregator, expected_tags):
    """
    Test the _get_connection method using the instant client
    """
    check = Oracle(CHECK_NAME, {'use_instant_client': True}, [instance])
    con = mock.MagicMock()
    with mock.patch('datadog_checks.oracle.oracle.oracledb') as pyoradb:
        pyoradb.connect.return_value = con
        dd_run_check(check)
        assert check._cached_connection == con
        pyoradb.connect.assert_called_with(user='system', password='oracle', dsn=check._get_dsn())
        aggregator.assert_service_check("oracle.can_connect", check.OK, count=1, tags=expected_tags)
        aggregator.assert_service_check("oracle.can_query", check.OK, count=1, tags=expected_tags)


def test__get_connection_oracldb_query_fail(check, dd_run_check, aggregator):
    """
    Test the _get_connection method using the oracle client and unsuccessfully query DB
    """
    con = mock.MagicMock()

    check._query_manager.executor = mock_bad_executor()
    expected_tags = ['server:localhost:1521', 'optional:tag1']

    with mock.patch('datadog_checks.oracle.oracle.oracledb') as pyoradb:
        pyoradb.connect.return_value = con
        dd_run_check(check)
        aggregator.assert_service_check("oracle.can_connect", check.OK, count=1, tags=expected_tags)
        aggregator.assert_service_check("oracle.can_query", check.CRITICAL, count=1, tags=expected_tags)


def test__get_connection_oracledb_server_incorrect_formatting(instance, dd_run_check, aggregator):
    """
    Test the _get_connection method using the instant client when the server is formatted incorrectly
    """
    con = mock.MagicMock()
    instance['server'] = 'localhost:1521a'
    check = Oracle(CHECK_NAME, {}, [instance])
    expected_tags = ['server:localhost:1521a', 'optional:tag1']
    with mock.patch('datadog_checks.oracle.oracle.oracledb') as pyoradb:
        pyoradb.connect.return_value = con
        dd_run_check(check)
        aggregator.assert_service_check("oracle.can_connect", check.CRITICAL, count=1, tags=expected_tags)
        aggregator.assert_service_check("oracle.can_query", check.CRITICAL, count=1, tags=expected_tags)
