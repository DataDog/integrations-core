# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from requests import ConnectionError

from datadog_checks.ibm_db2 import IbmDb2Check
from datadog_checks.ibm_db2.connection import get_connection_data
from datadog_checks.ibm_db2.utils import scrub_connection_string

pytestmark = pytest.mark.unit


class TestPasswordScrubber:
    def test_start(self):
        s = 'pwd=password;...'

        assert scrub_connection_string(s) == 'pwd=********;...'

    def test_end(self):
        s = '...;pwd=password'

        assert scrub_connection_string(s) == '...;pwd=********'

    def test_no_match_within_value(self):
        s = '...pwd=password;...'

        assert scrub_connection_string(s) == s


def test_retry_connection(aggregator, instance):
    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    conn1 = mock.MagicMock()
    ibmdb2._connection.conn = conn1

    def mock_exception(*args, **kwargs):
        raise ConnectionError("[IBM][CLI Driver] CLI0106E  Connection is closed. SQLSTATE=08003")

    with mock.patch('ibm_db.exec_immediate', side_effect=mock_exception):
        with mock.patch('ibm_db.connect', return_value=mock.MagicMock()):
            with pytest.raises(ConnectionError, match='CLI0106E  Connection is closed. SQLSTATE=08003'):
                ibmdb2.check(instance)
        # new connection made
        assert ibmdb2._connection.conn != conn1
    aggregator.assert_service_check(IbmDb2Check.SERVICE_CHECK_CONNECT, IbmDb2Check.OK)


def test_fails_to_reconnect(aggregator, instance):
    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    conn1 = mock.MagicMock()
    ibmdb2._connection.conn = conn1

    def mock_exception(*args, **kwargs):
        raise ConnectionError("[IBM][CLI Driver] CLI0106E  Connection is closed. SQLSTATE=08003")

    with mock.patch('ibm_db.exec_immediate', side_effect=mock_exception):
        with mock.patch('ibm_db.connect', side_effect=mock_exception):
            with pytest.raises(ConnectionError, match='Unable to create new connection'):
                ibmdb2.check(instance)
        # new connection could not be made
        assert ibmdb2._connection.conn is None
    aggregator.assert_service_check(IbmDb2Check.SERVICE_CHECK_CONNECT, IbmDb2Check.CRITICAL)


def test_ok_service_check_is_emitted_on_every_check_run(instance, aggregator):
    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._connection.conn = mock.MagicMock()
    with mock.patch('ibm_db.exec_immediate'):
        ibmdb2.check(instance)
    aggregator.assert_service_check(IbmDb2Check.SERVICE_CHECK_CONNECT, IbmDb2Check.OK)


def test_query_function_error(aggregator, instance):
    exception_msg = (
        '[IBM][CLI Driver][DB2/NT64] SQL0440N  No authorized routine named "MON_GET_INSTANCE" of type '
        '"FUNCTION" having compatible arguments was found.  SQLSTATE=42884'
    )

    def query_instance(*args, **kwargs):
        raise Exception(exception_msg)

    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2.log = mock.MagicMock()
    ibmdb2._connection.conn = mock.MagicMock()
    ibmdb2._connection.connect = mock.MagicMock()
    ibmdb2.query_instance = query_instance

    with pytest.raises(Exception):
        ibmdb2.query_instance()
        ibmdb2.log.warning.assert_called_with('Encountered error running `%s`: %s', 'query_instance', exception_msg)


def test_non_connection_errors_are_ignored(aggregator, instance):
    erroring_query = mock.Mock(side_effect=Exception("I'm broken"))
    erroring_query.__name__ = 'Erroring query'

    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._connection.conn = mock.MagicMock()
    ibmdb2._connection.connect = mock.MagicMock()
    ibmdb2._query_methods = (mock.Mock(), erroring_query, mock.Mock())

    ibmdb2.check(instance)
    for query_method in ibmdb2._query_methods:
        query_method.assert_called()


def test_connection_errors_stops_execution(aggregator, instance):
    erroring_query = mock.Mock(side_effect=ConnectionError("I'm broken"))
    erroring_query.__name__ = 'Erroring query'

    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._connection.conn = mock.MagicMock()
    ibmdb2._connection.connect = mock.MagicMock()
    ibmdb2._query_methods = (mock.Mock(), erroring_query, mock.Mock())

    with pytest.raises(ConnectionError):
        ibmdb2.check(instance)

    ibmdb2._query_methods[0].assert_called()
    ibmdb2._query_methods[1].assert_called()
    ibmdb2._query_methods[2].assert_not_called()


def test_parse_version(instance):
    raw_version = '11.01.0202'
    check = IbmDb2Check('ibm_db2', {}, [instance])
    expected = {
        'major': '11',
        'minor': '1',
        'mod': '2',
        'fix': '2',
    }
    assert check.parse_version(raw_version) == expected


def test_get_connection_data():
    expected = 'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1'
    assert (expected, '', '') == get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, 'none', None, None)

    expected = (
        'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1;'
        'security=ssl;sslservercertificate=/path/cert'
    )
    assert (expected, '', '') == get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, 'none', '/path/cert', None)

    expected = 'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1;connecttimeout=1'
    assert (expected, '', '') == get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, 'none', None, 1)


def test_cancel_closes_check_and_custom_query_connections(instance):
    instance['custom_queries'] = [{'metric_prefix': 'ibm_db2', 'query': 'SELECT 1', 'columns': [{}]}]
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check_conn = mock.MagicMock()
    job_conn = mock.MagicMock()
    check._connection.conn = check_conn
    check._custom_metrics._connection.conn = job_conn

    with mock.patch('ibm_db.close') as close:
        check.cancel()

    close.assert_has_calls([mock.call(job_conn), mock.call(check_conn)], any_order=True)
