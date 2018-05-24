# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import cx_Oracle
from datadog_checks.oracle import OracleConfigError


def test__get_config(check, instance):
    """
    Test the _get_config method
    """
    server, user, password, service, jdbc_driver, tags, custom_queries = check._get_config(instance)
    assert user == 'system'
    assert password == 'oracle'
    assert service == 'xe'
    assert jdbc_driver is None
    assert tags == ['optional:tag1']
    assert custom_queries == []
    assert check.server == 'localhost:1521'


def test_check_misconfig(check, instance):
    """
    Test bad config values
    """
    instance['server'] = None
    with pytest.raises(OracleConfigError):
        check.check(instance)


def test_client_fallback(check, instance):
    """
    Test the client fallback logic
    """
    check._get_connection = mock.MagicMock()
    with mock.patch('datadog_checks.oracle.oracle.cx_Oracle') as cx:
        check.check(instance)
        assert check.use_oracle_client is True
        cx.DatabaseError = cx_Oracle.DatabaseError
        cx.clientversion.side_effect = cx_Oracle.DatabaseError
        check.check(instance)
        assert check.use_oracle_client is False


def test__get_connection_instant_client(check, instance):
    """
    Test the _get_connection method using the instant client
    """
    check.use_oracle_client = True
    server, user, password, service, jdbc_driver, tags, _ = check._get_config(instance)
    con = mock.MagicMock()
    service_check = mock.MagicMock()
    check.service_check = service_check
    expected_tags = ['server:localhost:1521', 'optional:tag1']
    with mock.patch('datadog_checks.oracle.oracle.cx_Oracle') as cx:
        cx.connect.return_value = con
        ret = check._get_connection(server, user, password, service, jdbc_driver, tags)
        assert ret == con
        assert check.service_check_tags == expected_tags
        cx.connect.assert_called_with('system/oracle@//localhost:1521/xe')
        service_check.assert_called_with(check.SERVICE_CHECK_NAME, check.OK, tags=expected_tags)


def test__get_connection_jdbc(check, instance):
    """
    Test the _get_connection method using the JDBC client
    """
    check.use_oracle_client = False
    server, user, password, service, jdbc_driver, tags, _ = check._get_config(instance)
    con = mock.MagicMock()
    service_check = mock.MagicMock()
    check.service_check = service_check
    expected_tags = ['server:localhost:1521', 'optional:tag1']
    with mock.patch('datadog_checks.oracle.oracle.cx_Oracle'):
        with mock.patch('datadog_checks.oracle.oracle.jdb') as jdb:
            with mock.patch('datadog_checks.oracle.oracle.jpype') as jpype:
                jpype.isJVMStarted.return_value = False
                jdb.connect.return_value = con
                ret = check._get_connection(server, user, password, service, jdbc_driver, tags)
                assert ret == con
                assert check.service_check_tags == expected_tags
                jdb.connect.assert_called_with('oracle.jdbc.OracleDriver', 'jdbc:oracle:thin:@//localhost:1521/xe',
                                               ['system', 'oracle'], None)
                service_check.assert_called_with(check.SERVICE_CHECK_NAME, check.OK, tags=expected_tags)


def test__get_connection_failure(check, instance):
    """
    Test the right service check is sent upon _get_connection failures
    """
    check.use_oracle_client = True
    expected_tags = ['server:localhost:1521', 'optional:tag1']
    service_check = mock.MagicMock()
    check.service_check = service_check
    server, user, password, service, jdbc_driver, tags, _ = check._get_config(instance)
    with pytest.raises(Exception):
        check._get_connection(server, user, password, service, jdbc_driver, tags)
    service_check.assert_called_with(check.SERVICE_CHECK_NAME, check.CRITICAL, tags=expected_tags)


def test__get_custom_metrics_misconfigured(check):
    log = mock.MagicMock()
    gauge = mock.MagicMock()
    con = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.fetchone.return_value = ["foo", "bar"]
    con.cursor.return_value = cursor
    check.log = log
    check.gauge = gauge

    query = {}
    custom_queries = [query]

    # No metric_prefix
    check._get_custom_metrics(None, custom_queries, None)
    log.error.assert_called_once_with('custom query field `metric_prefix` is required')
    log.reset_mock()

    query["metric_prefix"] = "foo"

    # No query for metric_prefix
    check._get_custom_metrics(None, custom_queries, None)
    log.error.assert_called_once_with('custom query field `query` is required for metric_prefix `foo`')
    log.reset_mock()

    query["query"] = "bar"

    # No columns for metric_prefix
    check._get_custom_metrics(None, custom_queries, None)
    log.error.assert_called_once_with('custom query field `columns` is required for metric_prefix `foo`')
    log.reset_mock()

    query["columns"] = [{}]

    # Wrong number of columns
    check._get_custom_metrics(con, custom_queries, None)
    log.error.assert_called_once_with('query result for metric_prefix foo: expected 1 columns, got 2')
    log.reset_mock()

    col1 = {"name": "baz", "type": "tag"}
    col2 = {"foo": "bar"}
    columns = [col1, col2]
    query["columns"] = columns

    # No name in column
    check._get_custom_metrics(con, custom_queries, None)
    log.error.assert_called_once_with('column field `name` is required for metric_prefix `foo`')
    log.reset_mock()

    del col2["foo"]
    col2["name"] = "foo"

    # No type in column
    check._get_custom_metrics(con, custom_queries, None)
    log.error.assert_called_once_with('column field `type` is required for column `foo` of metric_prefix `foo`')
    log.reset_mock()

    col2["type"] = "invalid"

    # Invalid type column
    check._get_custom_metrics(con, custom_queries, None)
    log.error.assert_called_once_with('invalid submission method `invalid` for column `foo` of metric_prefix `foo`')
    log.reset_mock()

    col2["type"] = "gauge"

    # Non numeric value
    check._get_custom_metrics(con, custom_queries, None)
    log.error.assert_called_once_with('non-numeric value `bar` for metric column `foo` of metric_prefix `foo`')

    # No metric sent if errors
    gauge.assert_not_called()


def test__get_custom_metrics(aggregator, check):
    con = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.fetchone.side_effect = [
        ["tag_value1", "1"],
        [1, 2, "tag_value2"]
    ]
    con.cursor.return_value = cursor

    custom_queries = [
        {
            "metric_prefix": "oracle.test1",
            "query": "mocked",
            "columns": [
                {
                    "name": "tag_name",
                    "type": "tag"
                },
                {
                    "name": "metric",
                    "type": "gauge"
                }
            ],
            "tags": ["query_tags1"]
        },
        {
            "metric_prefix": "oracle.test2",
            "query": "mocked",
            "columns": [
                {
                    "name": "rate",
                    "type": "rate"
                },
                {
                    "name": "gauge",
                    "type": "gauge"
                },
                {
                    "name": "tag_name",
                    "type": "tag"
                }
            ],
            "tags": ["query_tags2"]
        }
    ]

    check._get_custom_metrics(con, custom_queries, ["custom_tag"])
    aggregator.assert_metric("oracle.test1.metric", value=1, count=1,
                             tags=["tag_name:tag_value1", "query_tags1", "custom_tag"])
    aggregator.assert_metric("oracle.test2.gauge", value=2, count=1, metric_type=aggregator.GAUGE,
                             tags=["tag_name:tag_value2", "query_tags2", "custom_tag"])
    aggregator.assert_metric("oracle.test2.rate", value=1, count=1, metric_type=aggregator.RATE,
                             tags=["tag_name:tag_value2", "query_tags2", "custom_tag"])


def test__get_sys_metrics(aggregator, check):
    query = "SELECT METRIC_NAME, VALUE, BEGIN_TIME FROM GV$SYSMETRIC ORDER BY BEGIN_TIME"
    con = mock.MagicMock()
    cur = mock.MagicMock()
    con.cursor.return_value = cur
    cur.fetchall.return_value = zip(check.SYS_METRICS.keys(), [0] * len(check.SYS_METRICS.keys()))

    check._get_sys_metrics(con, ["custom_tag"])

    cur.execute.assert_called_with(query)
    for _, metric in check.SYS_METRICS.items():
        aggregator.assert_metric(metric, count=1, value=0, tags=["custom_tag"])


def test__get_tablespace_metrics(aggregator, check):
    query = "SELECT TABLESPACE_NAME, sum(BYTES), sum(MAXBYTES) FROM sys.dba_data_files GROUP BY TABLESPACE_NAME"

    con = mock.MagicMock()
    cur = mock.MagicMock()
    cur.fetchall.return_value = [
        ["offline", None, 100],
        ["normal", 50, 100],
        ["full", 100, 100],
        ["size_0", 1, None]
    ]
    con.cursor.return_value = cur

    check._get_tablespace_metrics(con, ["custom_tag"])
    cur.execute.assert_called_with(query)

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
