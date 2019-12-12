# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

import mock

from .common import DB, HOST, PASSWORD, PORT, USERNAME

from datadog_checks.ibm_db2 import IbmDb2Check
from datadog_checks.ibm_db2.errors import ConnectionError
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

    def mock_exception():
        raise Exception("Connection is closed")

    with mock.patch('datadog_checks.ibm_db2.IbmDb2Check.get_connection', side_effect=mock_exception):

        with pytest.raises(Exception, match='Connection is closed'):
            ibmdb2.check(instance)
