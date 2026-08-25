# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os

import mock
import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.innodb_metrics import InnoDBMetrics

from . import common


def get_test_file_path(filename):
    return os.path.join(common.HERE, filename)


def get_innodb_status_fixture(version):
    with open(get_test_file_path(f'fixtures/innodb_status_{version}.txt')) as f:
        return f.read()


def get_innodb_status_result(version):
    with open(get_test_file_path(f'results/innodb_status_{version}.json')) as f:
        status = f.read()
        return json.loads(status)


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


@pytest.mark.unit
@pytest.mark.parametrize(
    'version',
    ['mysql_56', 'mysql_57', 'mysql_80', 'mysql_84', 'mariadb_106', 'mariadb_105', 'mariadb_1011', 'mariadb_111'],
)
def test_get_stats_from_innodb_status(caplog, version):
    caplog.at_level(logging.WARNING)
    idb = InnoDBMetrics()

    innodb_status = get_innodb_status_fixture(version)
    exepcted_result = get_innodb_status_result(version)

    db = mock.MagicMock()
    mocked_cursor = mock.MagicMock()
    db.cursor.return_value = mocked_cursor
    mocked_cursor.rowcount = 1
    mocked_cursor.fetchone.return_value = ('InnoDB', '', innodb_status)
    result = idb.get_stats_from_innodb_status(db)
    assert result == exepcted_result


@pytest.mark.unit
def test_check_innodb_engine_enabled_with_config_disabled():
    """Test that disable_innodb_metrics config properly disables InnoDB metrics collection"""

    # Create instance with disable_innodb_metrics set to True
    instance = {
        'host': 'localhost',
        'user': 'datadog',
        'options': {
            'disable_innodb_metrics': True,
        },
    }

    mysql_check = MySql(common.CHECK_NAME, {}, [instance])

    # Mock database connection
    db = mock.MagicMock()

    # Call the method
    result = mysql_check._check_innodb_engine_enabled(db)

    # Assert that InnoDB is disabled
    assert result is False

    # Verify database cursor was never called
    db.cursor.assert_not_called()
