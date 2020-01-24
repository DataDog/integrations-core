# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.ibm_db2 import IbmDb2Check
from datadog_checks.ibm_db2.utils import scrub_connection_string

from .common import DB2_VERSION

pytestmark = pytest.mark.unit

CHECK_ID = 'test:123'


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


def test_metadata(aggregator, instance, datadog_agent):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check_id = CHECK_ID

    check.check(instance)

    # only major and minor are consistent values
    major, minor = DB2_VERSION.split('.')

    version_metadata = {
        'version.scheme': 'ibm_db2',
        'version.major': '11',
        'version.minor': '1',
    }

    datadog_agent.assert_metadata(CHECK_ID, version_metadata)


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
