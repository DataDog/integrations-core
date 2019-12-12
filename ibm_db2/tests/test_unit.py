# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from mock import MagicMock

from .common import DB, HOST, PASSWORD, PORT, USERNAME

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


def test_cache_connection(aggregator, instance):
    instance['cache_connection'] = False
    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._set_conn_config = MagicMock()

    ibmdb2.check(ibmdb2.instance)
    ibmdb2._set_conn_config.assert_called()
    # Check that the connection config options are initialized
    assert ibmdb2._host == HOST
    assert ibmdb2._port == PORT
    assert ibmdb2._db == DB
    assert ibmdb2._username == USERNAME
    assert ibmdb2._password == PASSWORD

    # New host for self.instance
    ibmdb2.instance['host'] = 'test2'

    # Run check with self.instance
    ibmdb2.check(ibmdb2.instance)
    ibmdb2._set_conn_config.assert_called()
    # Check that the host has been updated
    assert ibmdb2._host == 'test2'
