# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess

import mock
import psutil
import pymysql
import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.version_utils import get_version

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


def test__get_server_pid():
    """
    Test the logic looping through the processes searching for `mysqld`
    """
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    mysql_check._get_pid_file_variable = mock.MagicMock(return_value=None)
    mysql_check.log = mock.MagicMock()
    dummy_proc = subprocess.Popen(["python"])

    p_iter = psutil.process_iter

    def process_iter():
        """
        Wrap `psutil.process_iter` with a func killing a running process
        while iterating to reproduce a bug in the pid detection.
        We don't use psutil directly here because at the time this will be
        invoked, `psutil.process_iter` will be mocked. Instead we assign it to
        `p_iter` which is then part of the closure (see line above).
        """
        for p in p_iter():
            if dummy_proc.pid == p.pid:
                dummy_proc.terminate()
                dummy_proc.wait()
            # continue as the original `process_iter` function
            yield p

    with mock.patch('datadog_checks.mysql.mysql.psutil.process_iter', process_iter):
        with mock.patch('datadog_checks.mysql.mysql.PROC_NAME', 'this_shouldnt_exist'):
            # the pid should be none but without errors
            assert mysql_check._get_server_pid(None) is None
            assert mysql_check.log.exception.call_count == 0


def test_parse_get_version():
    class MockCursor:
        version = (b'5.5.12-log',)

        def execute(self, command):
            pass

        def close(self):
            return MockCursor()

        def fetchone(self):
            return self.version

    class MockDatabase:
        def cursor(self):
            return MockCursor()

    mocked_db = MockDatabase()
    for mocked_db.version in [(b'5.5.12-log',), ('5.5.12-log',)]:
        v = get_version(mocked_db)
        assert v.version == '5.5.12'
        assert v.flavor == 'MySQL'
        assert v.build == 'log'


@pytest.mark.parametrize(
    'replica_io_running, replica_sql_running, source_host, slaves_connected, check_status_repl, check_status_source',
    [
        # Replica host only
        pytest.param(('Slave_IO_Running', {}), ('Slave_SQL_Running', {}), 'source', 0, MySql.CRITICAL, None),
        pytest.param(('Replica_IO_Running', {}), ('Replica_SQL_Running', {}), 'source', 0, MySql.CRITICAL, None),
        pytest.param(('Slave_IO_Running', {'a': 'yes'}), ('Slave_SQL_Running', {}), 'source', 0, MySql.WARNING, None),
        pytest.param(
            ('Replica_IO_Running', {'a': 'yes'}), ('Replica_SQL_Running', {}), 'source', 0, MySql.WARNING, None
        ),
        pytest.param(('Slave_IO_Running', {}), ('Slave_SQL_Running', {'a': 'yes'}), 'source', 0, MySql.WARNING, None),
        pytest.param(
            ('Replica_IO_Running', {}), ('Replica_SQL_Running', {'a': 'yes'}), 'source', 0, MySql.WARNING, None
        ),
        pytest.param(
            ('Slave_IO_Running', {'a': 'yes'}), ('Slave_SQL_Running', {'a': 'yes'}), 'source', 0, MySql.OK, None
        ),
        pytest.param(
            ('Replica_IO_Running', {'a': 'yes'}),
            ('Replica_SQL_Running', {'a': 'yes'}),
            'source',
            0,
            MySql.OK,
            None,
        ),
        # Source host only
        pytest.param(('Replica_IO_Running', None), ('Replica_SQL_Running', None), None, 1, None, MySql.OK),
        pytest.param(('Replica_IO_Running', None), ('Replica_SQL_Running', None), None, 0, None, MySql.WARNING),
        # Source and replica host
        pytest.param(('Replica_IO_Running', {}), ('Replica_SQL_Running', {}), 'source', 1, MySql.CRITICAL, MySql.OK),
        pytest.param(
            ('Replica_IO_Running', {'a': 'yes'}), ('Replica_SQL_Running', {}), 'source', 1, MySql.WARNING, MySql.OK
        ),
        pytest.param(
            ('Slave_IO_Running', {'a': 'yes'}),
            ('Slave_SQL_Running', {'a': 'yes'}),
            'source',
            1,
            MySql.OK,
            MySql.OK,
        ),
    ],
)
def test_replication_check_status(
    replica_io_running,
    replica_sql_running,
    source_host,
    slaves_connected,
    check_status_repl,
    check_status_source,
    instance_basic,
    aggregator,
):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_basic])
    mysql_check.service_check_tags = ['foo:bar']
    mocked_results = {
        'Slaves_connected': slaves_connected,
        'Binlog_enabled': True,
    }
    if replica_io_running[1] is not None:
        mocked_results[replica_io_running[0]] = replica_io_running[1]
    if replica_sql_running[1] is not None:
        mocked_results[replica_sql_running[0]] = replica_sql_running[1]
    if source_host:
        mocked_results['Master_Host'] = source_host

    mysql_check._check_replication_status(mocked_results)
    expected_service_check_len = 0

    if check_status_repl is not None:
        aggregator.assert_service_check(
            'mysql.replication.slave_running', check_status_repl, tags=['foo:bar', 'replication_mode:replica'], count=1
        )
        aggregator.assert_service_check(
            'mysql.replication.replica_running',
            check_status_repl,
            tags=['foo:bar', 'replication_mode:replica'],
            count=1,
        )
        expected_service_check_len += 1

    if check_status_source is not None:
        aggregator.assert_service_check(
            'mysql.replication.slave_running', check_status_source, tags=['foo:bar', 'replication_mode:source'], count=1
        )
        aggregator.assert_service_check(
            'mysql.replication.replica_running',
            check_status_source,
            tags=['foo:bar', 'replication_mode:source'],
            count=1,
        )
        expected_service_check_len += 1

    assert len(aggregator.service_checks('mysql.replication.slave_running')) == expected_service_check_len


def test__get_is_aurora():
    def new_check():
        return MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])

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
            return MockCursor([])

        def fetchall(self):
            return self.rows

    class MockDatabase:
        def __init__(self, cursor):
            self.cursor = cursor

        def cursor(self):
            return self.cursor

    check = new_check()
    assert True is check._get_is_aurora(MockDatabase(MockCursor(rows=[('1.72.1',)])))
    assert True is check._get_is_aurora(None)
    assert True is check._is_aurora

    check = new_check()
    assert True is check._get_is_aurora(
        MockDatabase(
            MockCursor(
                rows=[
                    ('1.72.1',),
                    ('1.72.1',),
                ]
            )
        )
    )
    assert True is check._get_is_aurora(None)
    assert True is check._is_aurora

    check = new_check()
    assert False is check._get_is_aurora(MockDatabase(MockCursor(rows=[])))
    assert False is check._get_is_aurora(None)
    assert False is check._is_aurora

    check = new_check()
    assert False is check._get_is_aurora(MockDatabase(MockCursor(rows=None, side_effect=ValueError())))
    assert None is check._is_aurora
    assert False is check._get_is_aurora(None)


@pytest.mark.parametrize(
    'disable_generic_tags, hostname, expected_tags',
    [
        (True, None, {'port:unix_socket', 'dd.internal.resource:database_instance:stubbed.hostname'}),
        (
            False,
            None,
            {'port:unix_socket', 'server:localhost', 'dd.internal.resource:database_instance:stubbed.hostname'},
        ),
        (True, 'foo', {'port:unix_socket', 'dd.internal.resource:database_instance:stubbed.hostname'}),
        (False, 'foo', {'port:unix_socket', 'server:foo', 'dd.internal.resource:database_instance:stubbed.hostname'}),
    ],
)
def test_service_check(disable_generic_tags, expected_tags, hostname):
    config = {'server': 'localhost', 'user': 'datadog', 'disable_generic_tags': disable_generic_tags}
    check = MySql(common.CHECK_NAME, {}, instances=[config])

    assert set(check._service_check_tags(hostname)) == expected_tags
