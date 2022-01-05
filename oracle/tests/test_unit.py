# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

import mock

from datadog_checks.base.utils.db import Query, QueryManager
from datadog_checks.oracle import Oracle, queries

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
            },
            ['server:localhost:2484', 'optional:tag1'],
        ),
    ],
)
def test__get_connection_instant_client(instance, dd_run_check, aggregator, expected_tags):
    """
    Test the _get_connection method using the instant client
    """
    check = Oracle(CHECK_NAME, {}, [instance])
    check.use_oracle_client = True
    con = mock.MagicMock()
    with mock.patch('datadog_checks.oracle.oracle.cx_Oracle') as cx:
        cx.connect.return_value = con
        dd_run_check(check)
        assert check._cached_connection == con
        cx.connect.assert_called_with(user='system', password='oracle', dsn=check._get_dsn())
        aggregator.assert_service_check("oracle.can_connect", check.OK, count=1, tags=expected_tags)
        aggregator.assert_service_check("oracle.can_query", check.OK, count=1, tags=expected_tags)


def test__get_connection_instant_client_query_fail(check, dd_run_check, aggregator):
    """
    Test the _get_connection method using the oracle client and unsuccessfully query DB
    """
    check.use_oracle_client = True
    con = mock.MagicMock()

    check._query_manager.executor = mock_bad_executor()
    expected_tags = ['server:localhost:1521', 'optional:tag1']

    with mock.patch('datadog_checks.oracle.oracle.cx_Oracle') as cx:
        cx.connect.return_value = con
        dd_run_check(check)
        aggregator.assert_service_check("oracle.can_connect", check.OK, count=1, tags=expected_tags)
        aggregator.assert_service_check("oracle.can_query", check.CRITICAL, count=1, tags=expected_tags)


def test__get_connection_instant_client_server_incorrect_formatting(instance, dd_run_check, aggregator):
    """
    Test the _get_connection method using the instant client when the server is formatted incorrectly
    """
    con = mock.MagicMock()
    instance['server'] = 'localhost:1521a'
    check = Oracle(CHECK_NAME, {}, [instance])
    check.use_oracle_client = True
    expected_tags = ['server:localhost:1521a', 'optional:tag1']
    with mock.patch('datadog_checks.oracle.oracle.cx_Oracle') as cx:
        cx.connect.return_value = con
        dd_run_check(check)
        aggregator.assert_service_check("oracle.can_connect", check.CRITICAL, count=1, tags=expected_tags)
        aggregator.assert_service_check("oracle.can_query", check.CRITICAL, count=1, tags=expected_tags)


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
    check.use_oracle_client = False
    con = mock.MagicMock()

    cx = mock.MagicMock(DatabaseError=RuntimeError)
    cx.clientversion.side_effect = cx.DatabaseError()

    jdb = mock.MagicMock()
    jdb.connect.return_value = con
    jpype = mock.MagicMock(isJVMStarted=lambda: False)

    mocks = [
        ('datadog_checks.oracle.oracle.cx_Oracle', cx),
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
    check.use_oracle_client = False
    con = mock.MagicMock()
    expected_tags = ['server:localhost:1521', 'optional:tag1']

    check._query_manager.executor = mock_bad_executor()
    cx = mock.MagicMock(DatabaseError=RuntimeError)
    cx.clientversion.side_effect = cx.DatabaseError()

    jdb = mock.MagicMock()
    jdb.connect.return_value = con
    jpype = mock.MagicMock(isJVMStarted=lambda: False)

    check._query_errors = 1

    mocks = [
        ('datadog_checks.oracle.oracle.cx_Oracle', cx),
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


def test__get_connection_failure(check, dd_run_check, aggregator):
    """
    Test the right service check is sent upon _get_connection failures
    """
    expected_tags = ['server:localhost:1521', 'optional:tag1']
    dd_run_check(check)

    aggregator.assert_service_check("oracle.can_connect", check.CRITICAL, count=1, tags=expected_tags)
    aggregator.assert_service_check("oracle.can_query", check.CRITICAL, count=1, tags=expected_tags)
    assert check._cached_connection is None


def test__check_only_custom_queries(instance):
    """
    Test the default metrics are not called when only_custom queries set to true
    """
    instance['only_custom_queries'] = True

    check = Oracle(CHECK_NAME, {}, [instance])

    assert check._query_manager.queries == []


def test__check_only_custom_queries_not_set(instance):
    """
    Test the default metrics are called when only_custom queries is not set
    """
    instance['only_custom_queries'] = False

    check = Oracle(CHECK_NAME, {}, [instance])

    assert check._query_manager.queries != []


def __test__check_only_custom_queries_set_false(check, instance):
    """
    Test the default metrics are called when only_custom queries is set to False
    """
    assert check._query_manager.queries != []


def test_sys_metrics(aggregator, check):
    con = mock.MagicMock()
    cur = mock.MagicMock()
    con.cursor.return_value = cur
    metrics = copy.deepcopy(queries.SystemMetrics['columns'][1]['items'])
    cur.fetchall.return_value = zip([0] * len(metrics.keys()), metrics.keys())

    check._cached_connection = con
    check._query_manager.queries = [Query(queries.SystemMetrics)]
    check._query_manager.tags = ['custom_tag']
    check._query_manager.compile_queries()
    check._query_manager.execute()

    for metric in metrics.values():
        aggregator.assert_metric('oracle.{}'.format(metric['name']), count=1, value=0, tags=['custom_tag'])


def test_process_metrics(aggregator, check):
    con = mock.MagicMock()
    cur = mock.MagicMock()
    con.cursor.return_value = cur
    metrics = copy.deepcopy(queries.ProcessMetrics['columns'][1:])
    programs = [
        "PSEUDO",
        "oracle@localhost.localdomain (PMON)",
        "oracle@localhost.localdomain (PSP0)",
        "oracle@localhost.localdomain (VKTM)",
    ]
    cur.fetchall.return_value = [[program] + ([0] * len(metrics)) for program in programs]

    check._cached_connection = con
    check._query_manager.queries = [Query(queries.ProcessMetrics)]
    check._query_manager.tags = ['custom_tag']
    check._query_manager.compile_queries()
    check._query_manager.execute()

    for i, metric in enumerate(metrics):
        expected_program = programs[i]
        aggregator.assert_metric(
            'oracle.{}'.format(metric['name']),
            count=1,
            value=0,
            tags=['custom_tag', 'program:{}'.format(expected_program)],
        )


def test_tablespace_metrics(aggregator, check):
    con = mock.MagicMock()
    cur = mock.MagicMock()
    cur.fetchall.return_value = [
        ["offline", 0, 100, 0, 1],
        ["normal", 50, 100, 50, 0],
        ["full", 100, 100, 100, 0],
        ["size_0", 1, 0, 100, 0],
    ]
    con.cursor.return_value = cur

    check._cached_connection = con
    check._query_manager.queries = [Query(queries.TableSpaceMetrics)]
    check._query_manager.tags = ['custom_tag']
    check._query_manager.compile_queries()
    check._query_manager.execute()

    # Offline tablespace
    tags = ["custom_tag", "tablespace:offline"]
    aggregator.assert_metric("oracle.tablespace.used", value=0, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.size", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.in_use", value=0, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.offline", value=1, count=1, tags=tags)

    # Normal tablespace
    tags = ["custom_tag", "tablespace:normal"]
    aggregator.assert_metric("oracle.tablespace.used", value=50, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.size", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.in_use", value=50, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.offline", value=0, count=1, tags=tags)

    # Full tablespace
    tags = ["custom_tag", "tablespace:full"]
    aggregator.assert_metric("oracle.tablespace.used", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.size", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.in_use", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.offline", value=0, count=1, tags=tags)

    # Size 0 tablespace
    tags = ["custom_tag", "tablespace:size_0"]
    aggregator.assert_metric("oracle.tablespace.used", value=1, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.size", value=0, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.in_use", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.offline", value=0, count=1, tags=tags)


def test_custom_metrics(aggregator, check):
    con = mock.MagicMock()
    cursor = mock.MagicMock()
    data = [[["tag_value1", "1"]], [[1, 2, "tag_value2"]]]
    cursor.fetchall.side_effect = lambda: iter(data.pop(0))
    con.cursor.return_value = cursor

    custom_queries = [
        {
            "metric_prefix": "oracle.test1",
            "query": "mocked",
            "columns": [{"name": "tag_name", "type": "tag"}, {"name": "metric", "type": "gauge"}],
            "tags": ["query_tags1"],
        },
        {
            "metric_prefix": "oracle.test2",
            "query": "mocked",
            "columns": [
                {"name": "rate", "type": "rate"},
                {"name": "gauge", "type": "gauge"},
                {"name": "tag_name", "type": "tag"},
            ],
            "tags": ["query_tags2"],
        },
    ]
    check.instance['custom_queries'] = custom_queries
    check._fix_custom_queries()
    check._cached_connection = con
    query_manager = QueryManager(check, check.execute_query_raw, tags=['custom_tag'])
    query_manager.compile_queries()

    query_manager.execute()

    aggregator.assert_metric(
        "oracle.test1.metric", value=1, count=1, tags=["tag_name:tag_value1", "query_tags1", "custom_tag"]
    )
    aggregator.assert_metric(
        "oracle.test2.gauge",
        value=2,
        count=1,
        metric_type=aggregator.GAUGE,
        tags=["tag_name:tag_value2", "query_tags2", "custom_tag"],
    )
    aggregator.assert_metric(
        "oracle.test2.rate",
        value=1,
        count=1,
        metric_type=aggregator.RATE,
        tags=["tag_name:tag_value2", "query_tags2", "custom_tag"],
    )


def test_custom_metrics_multiple_results(aggregator, check):
    con = mock.MagicMock()
    cursor = mock.MagicMock()
    data = [["tag_value1", "1"], ["tag_value2", "2"]]
    cursor.fetchall.side_effect = lambda: iter(data)
    con.cursor.return_value = cursor

    custom_queries = [
        {
            "metric_prefix": "oracle.test1",
            "query": "mocked",
            "columns": [{"name": "tag_name", "type": "tag"}, {"name": "metric", "type": "gauge"}],
            "tags": ["query_tags1"],
        }
    ]

    check.instance['custom_queries'] = custom_queries
    check._fix_custom_queries()
    check._cached_connection = con
    query_manager = QueryManager(check, check.execute_query_raw, tags=['custom_tag'])
    query_manager.compile_queries()

    query_manager.execute()

    aggregator.assert_metric(
        "oracle.test1.metric", value=1, count=1, tags=["tag_name:tag_value1", "query_tags1", "custom_tag"]
    )
    aggregator.assert_metric(
        "oracle.test1.metric", value=2, count=1, tags=["tag_name:tag_value2", "query_tags1", "custom_tag"]
    )
