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
from datadog_checks.mysql.schemas_legacy import MySqlSchemaCollectorLegacy, SubmitData
from datadog_checks.mysql.version_utils import parse_version

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


@pytest.mark.parametrize(
    'raw_version, version_comment, expected_version, expected_flavor, expected_build',
    [
        # MySQL versions
        ('5.5.12-log', None, '5.5.12', 'MySQL', 'log'),
        ('5.7.30-standard', None, '5.7.30', 'MySQL', 'standard'),
        ('8.0.25-debug', None, '8.0.25', 'MySQL', 'debug'),
        ('8.0.33-valgrind', None, '8.0.33', 'MySQL', 'valgrind'),
        ('8.0.35-embedded', None, '8.0.35', 'MySQL', 'embedded'),
        ('5.6.51', None, '5.6.51', 'MySQL', 'unspecified'),
        ('8.0.35', None, '8.0.35', 'MySQL', 'unspecified'),
        # MariaDB versions
        ('10.3.34-MariaDB', None, '10.3.34', 'MariaDB', 'unspecified'),
        ('10.4.24-MariaDB-log', None, '10.4.24', 'MariaDB', 'log'),
        ('11.0.2-MariaDB', None, '11.0.2', 'MariaDB', 'unspecified'),
        # Percona versions
        ('5.7.39-42', 'Percona Server (GPL), Release 42, Revision 8b0a379', '5.7.39', 'Percona', 'unspecified'),
        ('8.4.5-5', 'Percona Server (GPL), Release 5, Revision 3d3abca6', '8.4.5', 'Percona', 'unspecified'),
        ('5.7.40-43-standard', 'Percona Server (GPL), Release 43, Revision 1a2b3c4', '5.7.40', 'Percona', 'standard'),
    ],
)
def test_parse_version(raw_version, version_comment, expected_version, expected_flavor, expected_build):
    """Test parsing of MySQL, MariaDB, and Percona versions."""
    result = parse_version(raw_version, version_comment)

    assert result.version == expected_version
    assert result.flavor == expected_flavor
    assert result.build == expected_build


@pytest.mark.parametrize(
    'version, compat_version, expected_compatible',
    [
        # Basic version compatibility scenarios
        ('5.5.12', (5, 4, 0), True),  # older major.minor
        ('5.5.12', (5, 5, 15), False),  # newer patch
        ('5.5.12', (5, 6, 0), False),  # newer minor
        ('5.5.12', (8, 0, 0), False),  # newer major
        ('5.7.30', (5, 6, 0), True),  # older minor
        ('5.7.30', (5, 7, 35), False),  # newer patch
        ('5.7.30', (8, 0, 0), False),  # newer major
        ('8.0.25', (5, 7, 0), True),  # older major
        ('8.0.25', (8, 0, 30), False),  # newer patch
        ('8.0.25', (8, 1, 0), False),  # newer minor
        # MariaDB version compatibility
        ('10.3.34', (10, 3, 30), True),  # older patch
        ('10.3.34', (10, 3, 40), False),  # newer patch
        ('10.3.34', (10, 4, 0), False),  # newer minor
        # Edge cases - versions with letters in patch level
        ('5.0.51a', (5, 0, 50), True),  # patchlevel extracted as 51
        ('5.0.51a', (5, 0, 55), False),  # patchlevel extracted as 51
        ('5.7.30b', (5, 7, 25), True),  # patchlevel extracted as 30
        ('5.7.30b', (5, 7, 35), False),  # patchlevel extracted as 30
    ],
)
def test_version_compatible(version, compat_version, expected_compatible):
    """Test version compatibility checks - flavor and build don't affect compatibility."""
    from datadog_checks.mysql.version_utils import MySQLVersion

    # Use a single flavor/build since they don't affect version compatibility
    mysql_version = MySQLVersion(version, 'MySQL', 'unspecified')
    actual_compatible = mysql_version.version_compatible(compat_version)

    assert actual_compatible == expected_compatible, (
        f"Version {mysql_version.version} compatibility with {compat_version} "
        f"expected {expected_compatible}, got {actual_compatible}"
    )


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
    mysql_check.global_variables._variables = {'log_bin': 'ON'}  # Set binlog enabled to True for the test
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
    databases_data = MySqlSchemaCollectorLegacy({}, check, check._config)
    with (
        mock.patch('time.time', side_effect=[0, 9999999]),
        mock.patch(
            'datadog_checks.mysql.schemas_legacy.MySqlSchemaCollectorLegacy._get_tables',
            return_value=[{"name": "mytable1"}, {"name": "mytable2"}],
        ),
        mock.patch('datadog_checks.mysql.databases_data.DatabasesData._get_tables', return_value=[1, 2]),
    ):
        with pytest.raises(StopIteration):
            databases_data._fetch_database_data("dummy_cursor", time.time(), "my_db")


def test_submit_is_called_if_too_many_columns():
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = MySqlSchemaCollectorLegacy({}, check, check._config)
    with (
        mock.patch('time.time', side_effect=[0, 0]),
        mock.patch('datadog_checks.mysql.databases_data.DatabasesData._get_tables', return_value=[1, 2]),
        mock.patch('datadog_checks.mysql.schemas_legacy.SubmitData.submit') as mocked_submit,
        mock.patch(
            'datadog_checks.mysql.schemas_legacy.MySqlSchemaCollectorLegacy._get_tables_data',
            return_value=(1000_000, {"name": "my_table"}),
        ),
    ):
        databases_data._fetch_database_data("dummy_cursor", time.time(), "my_db")
        assert mocked_submit.call_count == 2


def test_exception_handling_by_do_for_dbs():
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = MySqlSchemaCollectorLegacy({}, check, check._config)
    with mock.patch(
        'datadog_checks.mysql.schemas_legacy.MySqlSchemaCollectorLegacy._fetch_database_data',
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
            [{'Source_UUID': 'source-uuid-123', 'Master_UUID': None}],
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
            [{'Master_UUID': 'master-uuid-789'}],
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
            [{'Source_UUID': None, 'Master_UUID': 'master-uuid-789'}],
            False,
            'server-uuid-456',
            None,
            None,
        ),
        # Test case 7: Primary with binlog enabled
        (True, False, False, [], True, 'server-uuid-456', 'server-uuid-456', 'primary'),
        # Test case 8: No replica status and binlog disabled
        (True, False, False, None, False, 'server-uuid-456', None, None),
        # Test case 9: Empty replica status dict
        (True, False, False, [], False, 'server-uuid-456', None, None),
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
    mysql_check.global_variables._variables = {'log_bin': 'ON' if binlog_enabled else 'OFF'}
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
