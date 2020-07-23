# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.ibm_db2 import IbmDb2Check
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
    ibmdb2._conn = conn1
    ibmdb2.get_connection = mock.MagicMock()

    exception_msg = "[IBM][CLI Driver] CLI0106E  Connection is closed. SQLSTATE=08003"

    def mock_exception(*args, **kwargs):
        raise Exception(exception_msg)

    with mock.patch('ibm_db.exec_immediate', side_effect=mock_exception):

        with pytest.raises(Exception, match='CLI0106E  Connection is closed. SQLSTATE=08003'):
            ibmdb2.check(instance)
        # new connection made
        assert ibmdb2._conn != conn1


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


def test_get_connection_data(instance):
    check = IbmDb2Check('ibm_db2', {}, [instance])

    expected = 'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1'
    assert (expected, '', '') == check.get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, None)

    expected = (
        'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1;'
        'security=ssl;sslservercertificate=/path/cert'
    )
    assert (expected, '', '') == check.get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, '/path/cert')
