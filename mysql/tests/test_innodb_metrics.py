# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.mysql.innodb_metrics import InnoDBMetrics


@pytest.mark.unit
def test_innodb_status_unicode_error(caplog):
    class MockCursor:
        def execute(self, command):
            raise UnicodeDecodeError('encoding', b'object', 0, 1, command)

        def close(self):
            return MockCursor()

    class MockDatabase:
        def cursor(self, cursor):
            return MockCursor()

    caplog.at_level(logging.WARNING)
    idb = InnoDBMetrics()
    assert idb.get_stats_from_innodb_status(MockDatabase()) == {}
    assert 'Unicode error while getting INNODB status' in caplog.text
