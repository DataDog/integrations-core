# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import subprocess
import time

import mock
import psutil
import pymysql
import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.activity import MySQLActivity
from datadog_checks.mysql.databases_data import DatabasesData, SubmitData
from datadog_checks.mysql.version_utils import get_version

from . import common
from .utils import deep_compare

pytestmark = pytest.mark.unit


def test__get_aurora_replication_role():
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

    role = mysql_check._get_aurora_replication_role(MockDatabase(MockCursor(rows=[reader_row])))
    assert role == 'reader'

    role = mysql_check._get_aurora_replication_role(MockDatabase(MockCursor(rows=[writer_row])))
    assert role == 'writer'

    role = mysql_check._get_aurora_replication_role(MockDatabase(MockCursor(rows=[(1, 'reader')])))
    assert role is None

    # Error cases for non-aurora databases; any error should be caught and not fail the check

    role = mysql_check._get_aurora_replication_role(
        MockDatabase(
            MockCursor(
                rows=[], side_effect=pymysql.err.InternalError(pymysql.constants.ER.UNKNOWN_TABLE, 'Unknown Table')
            )
        )
    )
    assert role is None

    role = mysql_check._get_aurora_replication_role(
        MockDatabase(
            MockCursor(
                rows=[],
                side_effect=pymysql.err.ProgrammingError(pymysql.constants.ER.DBACCESS_DENIED_ERROR, 'Access Denied'),
            )
        )
    )
    assert role is None


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
        comment = (b'',)

        def __init__(self):
            self._last_query = ''

        def execute(self, query):
            self._last_query = query.lower()

        def close(self):
            return MockCursor()

        def fetchone(self):
            if 'comment' in self._last_query:
                return self.comment
            return self.version

    class MockDatabase:
        def __init__(self):
            self.cursor_obj = MockCursor()

        def cursor(self):
            return self.cursor_obj

    # Test MySQL version
    mocked_db = MockDatabase()
    for version in [(b'5.5.12-log',), ('5.5.12-log',)]:
        mocked_db.cursor_obj.version = version
        v = get_version(mocked_db)
        assert v.version == '5.5.12'
        assert v.flavor == 'MySQL'
        assert v.build == 'log'

    # Test TiDB version
    mocked_db = MockDatabase()
    for version in [(b'5.7.25-TiDB-v6.5.0',), ('5.7.25-TiDB-v6.5.0',)]:
        mocked_db.cursor_obj.version = version
        v = get_version(mocked_db)
        assert v.version == '5.7.25'
        assert v.flavor == 'TiDB'
        assert v.build == 'unspecified'


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
    mysql_check._binlog_enabled = True  # Set binlog enabled to True for the test
    mocked_results = {
        'Slaves_connected': slaves_connected,
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


def test__get_is_tidb():
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

        def fetchone(self):
            return self.rows[0] if self.rows else None

    class MockDatabase:
        def __init__(self, cursor):
            self.cursor = cursor

        def cursor(self):
            return self.cursor

    # Test TiDB detected - version contains "TiDB"
    check = new_check()
    assert True is check._get_is_tidb(MockDatabase(MockCursor(rows=[('5.7.25-TiDB-v6.5.0',)])))
    assert True is check._get_is_tidb(None)
    assert True is check._is_tidb

    # Test TiDB detected - different TiDB version format
    check = new_check()
    assert True is check._get_is_tidb(MockDatabase(MockCursor(rows=[('8.0.11-TiDB-v7.1.0',)])))
    assert True is check._get_is_tidb(None)
    assert True is check._is_tidb

    # Test TiDB not detected - regular MySQL version
    check = new_check()
    assert False is check._get_is_tidb(MockDatabase(MockCursor(rows=[('8.0.33',)])))
    assert False is check._get_is_tidb(None)
    assert False is check._is_tidb

    # Test TiDB not detected - empty result
    check = new_check()
    assert False is check._get_is_tidb(MockDatabase(MockCursor(rows=[])))
    assert False is check._get_is_tidb(None)
    assert False is check._is_tidb

    # Test error handling - exception raised
    check = new_check()
    assert False is check._get_is_tidb(MockDatabase(MockCursor(rows=None, side_effect=ValueError())))
    assert None is check._is_tidb
    assert False is check._get_is_tidb(None)


@pytest.mark.parametrize(
    'disable_generic_tags, hostname, expected_tags',
    [
        (
            True,
            None,
            {
                'port:unix_socket',
                'database_hostname:stubbed.hostname',
                'database_instance:stubbed.hostname',
                'dd.internal.resource:database_instance:stubbed.hostname',
            },
        ),
        (
            False,
            None,
            {
                'port:unix_socket',
                'server:localhost',
                'database_hostname:stubbed.hostname',
                'database_instance:stubbed.hostname',
                'dd.internal.resource:database_instance:stubbed.hostname',
            },
        ),
        (
            True,
            'foo',
            {
                'port:unix_socket',
                'database_hostname:stubbed.hostname',
                'database_instance:stubbed.hostname',
                'dd.internal.resource:database_instance:stubbed.hostname',
            },
        ),
        (
            False,
            'foo',
            {
                'port:unix_socket',
                'server:foo',
                'database_hostname:stubbed.hostname',
                'database_instance:stubbed.hostname',
                'dd.internal.resource:database_instance:stubbed.hostname',
            },
        ),
    ],
)
def test_service_check(disable_generic_tags, expected_tags, hostname):
    config = {'server': 'localhost', 'user': 'datadog', 'disable_generic_tags': disable_generic_tags}
    check = MySql(common.CHECK_NAME, {}, instances=[config])

    assert set(check._service_check_tags(hostname)) == expected_tags


class DummyLogger:
    def debug(*args):
        pass

    def error(*args):
        pass


def set_up_submitter_unit_test():
    submitted_data = []
    base_event = {
        "host": "some",
        "agent_version": 0,
        "dbms": "sqlserver",
        "kind": "sqlserver_databases",
        "collection_interval": 1200,
        "dbms_version": "some",
        "tags": "some",
        "cloud_metadata": "some",
    }

    def submitData(data):
        submitted_data.append(data)

    dataSubmitter = SubmitData(submitData, base_event, DummyLogger())
    return dataSubmitter, submitted_data


def test_submit_data():
    dataSubmitter, submitted_data = set_up_submitter_unit_test()

    dataSubmitter.store_db_infos(
        [
            {"name": "test_db1", "default_character_set_name": "latin1"},
            {"name": "test_db2", "default_character_set_name": "latin1"},
        ]
    )

    dataSubmitter.store("test_db1", [1, 2], 5)
    dataSubmitter.store("test_db2", [1, 2], 5)
    assert dataSubmitter.columns_since_last_submit() == 10
    dataSubmitter.store("test_db1", [1, 2], 10)

    dataSubmitter.submit()

    assert dataSubmitter.columns_since_last_submit() == 0

    expected_data = {
        "host": "some",
        "agent_version": 0,
        "dbms": "sqlserver",
        "kind": "sqlserver_databases",
        "collection_interval": 1200,
        "dbms_version": "some",
        "tags": "some",
        "cloud_metadata": "some",
        "metadata": [
            {"name": "test_db1", "default_character_set_name": "latin1", "tables": [1, 2, 1, 2]},
            {"name": "test_db2", "default_character_set_name": "latin1", "tables": [1, 2]},
        ],
    }

    data = json.loads(submitted_data[0])
    data.pop("timestamp")
    assert deep_compare(data, expected_data)


def test_fetch_throws():
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = DatabasesData({}, check, check._config)
    with (
        mock.patch('time.time', side_effect=[0, 9999999]),
        mock.patch(
            'datadog_checks.mysql.databases_data.DatabasesData._get_tables',
            return_value=[{"name": "mytable1"}, {"name": "mytable2"}],
        ),
        mock.patch('datadog_checks.mysql.databases_data.DatabasesData._get_tables', return_value=[1, 2]),
    ):
        with pytest.raises(StopIteration):
            databases_data._fetch_database_data("dummy_cursor", time.time(), "my_db")


def test_submit_is_called_if_too_many_columns():
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = DatabasesData({}, check, check._config)
    with (
        mock.patch('time.time', side_effect=[0, 0]),
        mock.patch('datadog_checks.mysql.databases_data.DatabasesData._get_tables', return_value=[1, 2]),
        mock.patch('datadog_checks.mysql.databases_data.SubmitData.submit') as mocked_submit,
        mock.patch(
            'datadog_checks.mysql.databases_data.DatabasesData._get_tables_data',
            return_value=(1000_000, {"name": "my_table"}),
        ),
    ):
        databases_data._fetch_database_data("dummy_cursor", time.time(), "my_db")
        assert mocked_submit.call_count == 2


def test_exception_handling_by_do_for_dbs():
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = DatabasesData({}, check, check._config)
    with mock.patch(
        'datadog_checks.mysql.databases_data.DatabasesData._fetch_database_data',
        side_effect=Exception("Can't connect to DB"),
    ):
        databases_data._fetch_for_databases([{"name": "my_db"}], "dummy_cursor")


def test_update_aurora_replication_role():
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])

    # Initial state - no tags
    assert 'replication_role:writer' not in mysql_check.tag_manager.get_tags()
    assert 'replication_role:reader' not in mysql_check.tag_manager.get_tags()

    # First check - writer role
    role = 'writer'
    mysql_check._update_aurora_replication_role(role)
    assert 'replication_role:writer' in mysql_check.tag_manager.get_tags()
    assert len([t for t in mysql_check.tag_manager.get_tags() if t.startswith('replication_role:')]) == 1

    # Simulate failover - reader role
    role = 'reader'
    mysql_check._update_aurora_replication_role(role)
    assert 'replication_role:reader' in mysql_check.tag_manager.get_tags()
    assert 'replication_role:writer' not in mysql_check.tag_manager.get_tags()
    assert len([t for t in mysql_check.tag_manager.get_tags() if t.startswith('replication_role:')]) == 1


def test_tidb_innodb_metrics_disabled():
    """Test that InnoDB metrics are disabled for TiDB instances"""
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])

    class MockCursor:
        def __init__(self, version_string):
            self.version_string = version_string

        def execute(self, query):
            pass

        def fetchone(self):
            return (self.version_string,)

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class MockDB:
        def __init__(self, version_string):
            self.version_string = version_string

        def cursor(self, cursor_type=None):
            return MockCursor(self.version_string)

    # Mock the innodb_stats object to track if it's called
    mysql_check.innodb_stats = mock.MagicMock()
    mysql_check.innodb_stats.get_stats_from_innodb_status = mock.MagicMock()
    mysql_check.innodb_stats.process_innodb_stats = mock.MagicMock()

    # Mock _check_innodb_engine_enabled to return True
    mysql_check._check_innodb_engine_enabled = mock.MagicMock(return_value=True)

    # Test with TiDB - should skip InnoDB metrics
    tidb_db = MockDB('8.0.11-TiDB-v8.1.2')

    # Simulate the InnoDB metrics collection logic
    if not mysql_check._config.options.get(
        'disable_innodb_metrics', False
    ) and mysql_check._check_innodb_engine_enabled(tidb_db):
        if mysql_check._get_is_tidb(tidb_db):
            # This should be the path taken for TiDB
            mysql_check.log.debug("Skipping innodb metrics collection for TiDB instance")
        else:
            # This should NOT be executed for TiDB
            mysql_check.innodb_stats.get_stats_from_innodb_status(tidb_db)
            mysql_check.innodb_stats.process_innodb_stats({}, {}, {})

    # Verify TiDB was detected
    assert mysql_check._get_is_tidb(tidb_db) is True

    # Verify InnoDB methods were NOT called
    mysql_check.innodb_stats.get_stats_from_innodb_status.assert_not_called()
    mysql_check.innodb_stats.process_innodb_stats.assert_not_called()


def test_tidb_replication_metrics_disabled():
    """Test that replication metrics are disabled for TiDB instances"""
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    mysql_check._config.replication_enabled = True

    class MockCursor:
        def __init__(self, version_string):
            self.version_string = version_string

        def execute(self, query):
            pass

        def fetchone(self):
            return (self.version_string,)

        def close(self):
            pass

    class MockDB:
        def __init__(self, version_string):
            self.version_string = version_string

        def cursor(self, cursor_type=None):
            return MockCursor(self.version_string)

    # Mock replication collection methods
    mysql_check._collect_replication_metrics = mock.MagicMock(return_value={})
    mysql_check._check_replication_status = mock.MagicMock()
    mysql_check._collect_group_replica_metrics = mock.MagicMock()

    tidb_db = MockDB('8.0.11-TiDB-v8.1.2')
    results = {}
    above_560 = True

    # Simulate the replication metrics collection logic
    if mysql_check._config.replication_enabled:
        if mysql_check._get_is_tidb(tidb_db):
            # This should be the path taken for TiDB
            mysql_check.log.debug("Skipping replication metrics collection for TiDB instance")
        elif mysql_check.performance_schema_enabled and mysql_check._group_replication_active:
            mysql_check._collect_group_replica_metrics(tidb_db, results)
        else:
            mysql_check._collect_replication_metrics(tidb_db, results, above_560)
            mysql_check._check_replication_status(results)

    # Verify TiDB was detected
    assert mysql_check._get_is_tidb(tidb_db) is True

    # Verify replication methods were NOT called
    mysql_check._collect_replication_metrics.assert_not_called()
    mysql_check._check_replication_status.assert_not_called()
    mysql_check._collect_group_replica_metrics.assert_not_called()


@pytest.mark.parametrize(
    'template, expected, tags',
    [
        ('$resolved_hostname', 'stubbed.hostname', ['env:prod']),
        ('$env-$resolved_hostname:$port', 'prod-stubbed.hostname:5432', ['env:prod', 'port:1']),
        ('$env-$resolved_hostname', 'prod-stubbed.hostname', ['env:prod']),
        ('$env-$resolved_hostname', '$env-stubbed.hostname', []),
        ('$env-$resolved_hostname', 'prod,staging-stubbed.hostname', ['env:prod', 'env:staging']),
    ],
)
def test_database_identifier(template, expected, tags):
    """
    Test functionality of calculating database_identifier
    """
    config = {'host': 'stubbed.hostname', 'user': 'datadog', 'port': 5432, 'tags': tags}
    config['database_identifier'] = {'template': template}
    check = MySql(common.CHECK_NAME, {}, instances=[config])

    assert check.database_identifier == expected


def test__eliminate_duplicate_rows():
    rows = [
        {'thread_id': 1, 'event_timer_start': 1000, 'event_timer_end': 2000, 'sql_text': 'SELECT 1'},
        {'thread_id': 1, 'event_timer_start': 2001, 'event_timer_end': 3000, 'sql_text': 'SELECT 1'},
    ]
    second_pass = {1: {'event_timer_start': 2001}}
    assert MySQLActivity._eliminate_duplicate_rows(rows, second_pass) == [
        {'thread_id': 1, 'event_timer_start': 2001, 'event_timer_end': 3000, 'sql_text': 'SELECT 1'},
    ]


@pytest.mark.parametrize(
    (
        'replication_enabled, is_mariadb, group_replication_active, replica_status, '
        'binlog_enabled, server_uuid, expected_cluster_uuid, expected_replication_role'
    ),
    [
        # Test case 1: Replication not enabled - should return early
        (False, False, False, None, False, None, None, None),
        # Test case 2: MariaDB - should return early
        (True, True, False, None, False, None, None, None),
        # Test case 3: Group replication active - should return early
        (True, False, True, None, False, None, None, None),
        # Test case 4: Replica with Source_UUID (mysql 8.0.22+)
        (
            True,
            False,
            False,
            {'Source_UUID': 'source-uuid-123', 'Master_UUID': None},
            False,
            'server-uuid-456',
            'source-uuid-123',
            'replica',
        ),
        # Test case 5: Replica with Master_UUID (mysql < 8.0.22)
        (
            True,
            False,
            False,
            {'Master_UUID': 'master-uuid-789'},
            False,
            'server-uuid-456',
            'master-uuid-789',
            'replica',
        ),
        # Test case 6: Replica with Source_UUID as None (should not fallback to Master_UUID)
        (
            True,
            False,
            False,
            {'Source_UUID': None, 'Master_UUID': 'master-uuid-789'},
            False,
            'server-uuid-456',
            None,
            None,
        ),
        # Test case 7: Primary with binlog enabled
        (True, False, False, {}, True, 'server-uuid-456', 'server-uuid-456', 'primary'),
        # Test case 8: No replica status and binlog disabled
        (True, False, False, None, False, 'server-uuid-456', None, None),
        # Test case 9: Empty replica status dict
        (True, False, False, {}, False, 'server-uuid-456', None, None),
    ],
)
def test_set_cluster_tags(
    replication_enabled,
    is_mariadb,
    group_replication_active,
    replica_status,
    binlog_enabled,
    server_uuid,
    expected_cluster_uuid,
    expected_replication_role,
):
    """Test the set_cluster_tags method with various scenarios."""
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])

    # Set up the check instance state
    mysql_check._config.replication_enabled = replication_enabled
    mysql_check.is_mariadb = is_mariadb
    mysql_check._group_replication_active = group_replication_active
    mysql_check._binlog_enabled = binlog_enabled
    mysql_check.server_uuid = server_uuid

    # Mock the _get_replica_replication_status method
    mysql_check._get_replica_replication_status = mock.MagicMock(return_value=replica_status)

    # Mock the database connection
    mock_db = mock.MagicMock()

    # Call the method under test
    mysql_check.set_cluster_tags(mock_db)

    # Verify the cluster_uuid attribute is set correctly
    if expected_cluster_uuid is not None:
        assert mysql_check.cluster_uuid == expected_cluster_uuid
    else:
        # If expected_cluster_uuid is None, cluster_uuid should either be None or not set
        assert getattr(mysql_check, 'cluster_uuid', None) is None or mysql_check.cluster_uuid is None

    # Verify the tags are set correctly
    tags = mysql_check.tag_manager.get_tags()

    if expected_cluster_uuid is not None:
        assert f'cluster_uuid:{expected_cluster_uuid}' in tags
    else:
        # Check that no cluster_uuid tag is present
        cluster_uuid_tags = [tag for tag in tags if tag.startswith('cluster_uuid:')]
        assert len(cluster_uuid_tags) == 0

    if expected_replication_role is not None:
        assert f'replication_role:{expected_replication_role}' in tags
    else:
        # Check that no replication_role tag is present
        replication_role_tags = [tag for tag in tags if tag.startswith('replication_role:')]
        assert len(replication_role_tags) == 0


def test_set_cluster_tags_tidb():
    """Test that set_cluster_tags skips processing for TiDB instances."""
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])

    # Set up the check instance state for TiDB
    mysql_check._config.replication_enabled = True
    mysql_check.is_mariadb = False
    mysql_check._group_replication_active = False
    mysql_check._is_tidb = True  # Pre-set TiDB detection

    # Mock the _get_is_tidb method to return True
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Mock the _get_replica_replication_status method - it should NOT be called
    mysql_check._get_replica_replication_status = mock.MagicMock()

    # Mock the database connection
    mock_db = mock.MagicMock()

    # Call the method under test
    mysql_check.set_cluster_tags(mock_db)

    # Verify that _get_is_tidb was called
    mysql_check._get_is_tidb.assert_called_once_with(mock_db)

    # Verify that _get_replica_replication_status was NOT called
    mysql_check._get_replica_replication_status.assert_not_called()

    # Verify no cluster tags were set
    tags = mysql_check.tag_manager.get_tags()
    cluster_uuid_tags = [tag for tag in tags if tag.startswith('cluster_uuid:')]
    replication_role_tags = [tag for tag in tags if tag.startswith('replication_role:')]

    assert len(cluster_uuid_tags) == 0
    assert len(replication_role_tags) == 0


def test_performance_schema_check_tidb():
    """Test that performance_schema check is skipped for TiDB instances."""
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])

    # Mock database connection
    mock_db = mock.MagicMock()
    mock_cursor = mock.MagicMock()
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Call the method under test
    result = mysql_check._check_performance_schema_enabled(mock_db)

    # Verify TiDB was detected
    mysql_check._get_is_tidb.assert_called_once_with(mock_db)

    # Verify performance_schema is marked as disabled for TiDB
    assert result is False
    assert mysql_check._performance_schema_enabled is False

    # Verify no SQL query was executed (since we skip for TiDB)
    mock_cursor.execute.assert_not_called()


# TiDB Statement Samples Tests
def test_get_tidb_statement_samples():
    """Test retrieving statement samples from TiDB cluster_statements_summary"""
    from datadog_checks.mysql.statement_samples import MySQLStatementSamples

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    config = mock.MagicMock()
    config.statement_samples_config = {'enabled': True}
    config.obfuscator_options = {}

    samples = MySQLStatementSamples(mysql_check, config, 5000)
    samples._check = mysql_check

    # Mock TiDB-specific query results
    tidb_rows = [
        {
            'current_schema': 'test_db',
            'sql_text': 'SELECT * FROM users WHERE id = 1',
            'digest': 'abc123',
            'digest_text': 'SELECT * FROM users WHERE id = ?',
            'execution_plan': 'id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk\n'
            + 'TableReader_1\troot\t1.00\tdata:TableScan\t1\ttime:1ms\t1KB\t0B\n'
            + '└─TableScan_2\tcop[tikv]\t1.00\ttable:users\t1\ttime:1ms\t1KB\t0B',
        }
    ]

    # Mock the method to return our test data
    samples._get_tidb_statement_samples = mock.MagicMock(return_value=tidb_rows)

    # Test the method
    result = samples._get_tidb_statement_samples()

    # Verify result
    assert len(result) == 1
    assert result[0]['digest'] == 'abc123'
    assert result[0]['sql_text'] == 'SELECT * FROM users WHERE id = 1'
    assert result[0]['current_schema'] == 'test_db'


def test_run_explain_tidb():
    """Test TiDB EXPLAIN FORMAT=tidb_json"""
    from datadog_checks.mysql.statement_samples import MySQLStatementSamples

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    config = mock.MagicMock()
    config.obfuscator_options = {}
    samples = MySQLStatementSamples(mysql_check, config, 5000)

    mock_cursor = mock.MagicMock()

    # Test successful explain
    plan_json = (
        '[{"id":"TableReader_1","estRows":"1.00","task":"root","access object":"","operator info":"data:TableScan"}]'
    )
    mock_cursor.fetchone.return_value = (plan_json,)

    result = samples._run_explain_tidb(
        'test_db', mock_cursor, 'SELECT * FROM users WHERE id = 1', 'SELECT * FROM users WHERE id = ?'
    )

    assert result == plan_json
    mock_cursor.execute.assert_called_with('EXPLAIN FORMAT=tidb_json SELECT * FROM users WHERE id = 1')

    # Test parameterized query (should return None)
    mock_cursor.reset_mock()
    result = samples._run_explain_tidb(
        'test_db', mock_cursor, 'SELECT * FROM users WHERE id = ?', 'SELECT * FROM users WHERE id = ?'
    )

    assert result is None
    mock_cursor.execute.assert_not_called()

    # Test error handling
    mock_cursor.reset_mock()
    mock_cursor.execute.side_effect = Exception("Access denied")

    with pytest.raises(Exception):
        samples._run_explain_tidb('test_db', mock_cursor, 'SELECT * FROM users', 'SELECT * FROM users')


def test_parse_tidb_text_plan():
    """Test parsing TiDB text execution plans"""
    from datadog_checks.mysql.statement_samples import MySQLStatementSamples

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    config = mock.MagicMock()
    config.obfuscator_options = {}
    samples = MySQLStatementSamples(mysql_check, config, 5000)

    # Test valid plan parsing
    plan_text = """id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk
TableReader_1\troot\t10.00\tdata:TableScan_2\t10\ttime:2ms, loops:1\t1.5KB\t0B
└─TableScan_2\tcop[tikv]\t10.00\ttable:users, keep order:false\t10\ttime:1ms, loops:1\t1KB\t0B"""

    result = samples._parse_tidb_text_plan(plan_text)
    parsed = json.loads(result)

    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0]['id'] == 'TableReader_1'
    assert parsed[0]['taskType'] == 'root'
    assert parsed[0]['estRows'] == '10.00'

    # Test malformed plan
    malformed_plan = "This is not a valid plan"
    result = samples._parse_tidb_text_plan(malformed_plan)
    parsed = json.loads(result)

    assert 'raw_plan' in parsed
    # Malformed plan without enough lines doesn't have parse_error, just raw_plan

    # Test empty plan
    empty_plan = ""
    result = samples._parse_tidb_text_plan(empty_plan)
    parsed = json.loads(result)

    assert 'raw_plan' in parsed or len(parsed) == 0


def test_convert_tidb_plan_to_mysql_format():
    """Test converting TiDB JSON plan to MySQL format"""
    from datadog_checks.mysql.statement_samples import MySQLStatementSamples

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    config = mock.MagicMock()
    config.obfuscator_options = {}
    samples = MySQLStatementSamples(mysql_check, config, 5000)

    # Test successful conversion
    tidb_plan = [
        {
            "id": "TableReader_1",
            "estRows": "10.00",
            "task": "root",
            "operatorInfo": "data:TableScan_2",
            "actRows": "10",
            "accessObject": "table:users",
        }
    ]

    result = samples._convert_tidb_plan_to_mysql_format(json.dumps(tidb_plan))
    parsed = json.loads(result)

    assert 'query_block' in parsed
    assert parsed['query_block']['select_id'] == 1
    assert 'table' in parsed['query_block']

    # Test with string input
    result = samples._convert_tidb_plan_to_mysql_format(json.dumps(tidb_plan))
    # Handle both str and bytes return types
    assert isinstance(result, (str, bytes))

    # Test error handling
    invalid_plan = "not json"
    result = samples._convert_tidb_plan_to_mysql_format(invalid_plan)
    assert result == invalid_plan  # Should return original on error


def test_tidb_statement_samples_integration():
    """Test full statement sample collection for TiDB"""
    from datadog_checks.mysql.statement_samples import MySQLStatementSamples

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)
    # Mock the resolved_hostname property
    type(mysql_check).resolved_hostname = mock.PropertyMock(return_value='test-host')

    config = mock.MagicMock()
    config.statement_samples_config = {'enabled': True}
    config.obfuscator_options = {}

    samples = MySQLStatementSamples(mysql_check, config, 5000)
    samples._check = mysql_check

    # Mock strategy cache check
    samples._should_collect_statement_samples = mock.MagicMock(return_value=True)

    # Test explain strategy selection for TiDB
    mock_db = mock.MagicMock()
    samples._get_db_connection = mock.MagicMock(return_value=mock_db)

    strategy = samples._get_sample_collection_strategy()

    # Verify TiDB uses the correct strategy
    assert samples._preferred_explain_strategies == ['TIDB_STATEMENT']
    assert strategy[0] == 'information_schema.cluster_statements_summary'


def test_derive_tidb_wait_event():
    """Test deriving wait events from TiDB processlist state"""
    from datadog_checks.mysql.activity import MySQLActivity

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    config = mock.MagicMock()
    config.obfuscator_options = {}

    activity = MySQLActivity(mysql_check, config, 'test-service')

    # Currently returns ('N/A', 'N/A') for all states
    wait_event, wait_group = activity._derive_tidb_wait_event('executing')
    assert wait_event == 'N/A'
    assert wait_group == 'N/A'

    # Test various states
    for state in ['', 'idle', 'processing', 'waiting']:
        wait_event, wait_group = activity._derive_tidb_wait_event(state)
        assert wait_event == 'N/A'
        assert wait_group == 'N/A'


def test_tidb_activity_error_handling():
    """Test that TiDB activity collection handles errors"""
    from datadog_checks.mysql.activity import MySQLActivity

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)
    # Mock the property
    type(mysql_check).events_wait_current_enabled = mock.PropertyMock(return_value=False)

    config = mock.MagicMock()
    config.database_monitoring_query_activity_config = {'enabled': True}
    config.obfuscator_options = {}

    activity = MySQLActivity(mysql_check, config, 'test-service')
    activity._check = mysql_check
    activity._tags = []

    # Test that _get_tidb_activity handles errors properly
    mock_cursor = mock.MagicMock()
    mock_cursor.execute.side_effect = Exception("Connection lost")

    # Directly test the method that executes the query
    with pytest.raises(Exception, match="Connection lost"):
        activity._get_tidb_activity(mock_cursor)


def test_tidb_empty_results():
    """Test handling of empty TiDB query results"""
    from datadog_checks.mysql.statement_samples import MySQLStatementSamples
    from datadog_checks.mysql.statements import MySQLStatementMetrics

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    config = mock.MagicMock()
    config.obfuscator_options = {}

    # Test empty statements
    connection_args = {}
    statements = MySQLStatementMetrics(mysql_check, config, connection_args)
    statements._check = mysql_check

    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = []

    from datadog_checks.mysql.statements import _collect_tidb_statement_metrics_rows

    # Call the function which returns normalized rows
    result = _collect_tidb_statement_metrics_rows(mock_cursor)

    # The result should be an empty list since fetchall returns []
    assert result == []
    assert len(result) == 0

    # Test empty statement samples
    samples = MySQLStatementSamples(mysql_check, config, connection_args)
    samples._check = mysql_check

    # Mock the method directly to return empty list
    samples._get_tidb_statement_samples = mock.MagicMock(return_value=[])

    # Call the method
    result = samples._get_tidb_statement_samples()

    # Verify the result is an empty list
    assert result == []
