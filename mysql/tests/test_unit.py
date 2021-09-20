# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pymysql
import pytest

from datadog_checks.mysql import MySql

from . import common

pytestmark = pytest.mark.unit


def test__get_runtime_aurora_tags():
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])

    class MockCursor:
        def __init__(self, rows, side_effect=None):
            self.rows = rows
            self.side_effect = side_effect

        def __call__(self, *args, **kwargs):
            return self

        def execute(self, command):
            if self.side_effect:
                raise self.side_effect

        def close(self):
            return MockCursor(None)

        def fetchone(self):
            return self.rows.pop(0)

    class MockDatabase:
        def __init__(self, cursor):
            self.cursor = cursor

        def cursor(self):
            return self.cursor

    reader_row = ('reader',)
    writer_row = ('writer',)

    tags = mysql_check._get_runtime_aurora_tags(MockDatabase(MockCursor(rows=[reader_row])))
    assert tags == ['replication_role:reader']

    tags = mysql_check._get_runtime_aurora_tags(MockDatabase(MockCursor(rows=[writer_row])))
    assert tags == ['replication_role:writer']

    tags = mysql_check._get_runtime_aurora_tags(MockDatabase(MockCursor(rows=[(1, 'reader')])))
    assert tags == []

    # Error cases for non-aurora databases; any error should be caught and not fail the check

    tags = mysql_check._get_runtime_aurora_tags(
        MockDatabase(
            MockCursor(
                rows=[], side_effect=pymysql.err.InternalError(pymysql.constants.ER.UNKNOWN_TABLE, 'Unknown Table')
            )
        )
    )
    assert tags == []

    tags = mysql_check._get_runtime_aurora_tags(
        MockDatabase(
            MockCursor(
                rows=[],
                side_effect=pymysql.err.ProgrammingError(pymysql.constants.ER.DBACCESS_DENIED_ERROR, 'Access Denied'),
            )
        )
    )
    assert tags == []


@pytest.mark.parametrize(
    'disable_generic_tags, hostname, expected_tags',
    [
        (True, None, ['mysql_server:localhost', 'port:unix_socket']),
        (False, None, ['mysql_server:localhost', 'port:unix_socket', 'server:localhost']),
        (True, 'foo', ['mysql_server:foo', 'port:unix_socket']),
        (False, 'foo', ['mysql_server:foo', 'port:unix_socket', 'server:foo']),
    ],
)
def test_service_check_tags_no_hostname(disable_generic_tags, expected_tags, hostname):
    config = {'server': 'localhost', 'user': 'datadog', 'disable_generic_tags': disable_generic_tags}
    check = MySql(common.CHECK_NAME, {}, instances=[config])

    assert check._service_check_tags(hostname) == expected_tags
