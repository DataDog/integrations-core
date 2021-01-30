# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import subprocess
from contextlib import closing
from os import environ

import mock
import psutil
import pytest
from pkg_resources import parse_version

from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.mysql import MySql, statements
from datadog_checks.mysql.version_utils import get_version

from . import common, tags, variables
from .common import MYSQL_VERSION_PARSED


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_minimal_config(aggregator, instance_basic):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    mysql_check.check(instance_basic)

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS_MIN, count=1)

    # Test metrics
    testable_metrics = (
        variables.STATUS_VARS
        + variables.VARIABLES_VARS
        + variables.INNODB_VARS
        + variables.BINLOG_VARS
        + variables.SYSTEM_METRICS
        + variables.SYNTHETIC_VARS
    )

    for mname in testable_metrics:
        aggregator.assert_metric(mname, at_least=0)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_complex_config(aggregator, instance_complex):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_complex])
    mysql_check.check(instance_complex)

    _assert_complex_config(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance_complex):
    aggregator = dd_agent_check(instance_complex)

    _assert_complex_config(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=['alice.age', 'bob.age'])


def _assert_complex_config(aggregator):
    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS, count=1)
    aggregator.assert_service_check('mysql.replication.slave_running', status=MySql.OK, tags=tags.SC_TAGS, at_least=1)
    testable_metrics = (
        variables.STATUS_VARS
        + variables.VARIABLES_VARS
        + variables.INNODB_VARS
        + variables.BINLOG_VARS
        + variables.SYSTEM_METRICS
        + variables.SCHEMA_VARS
        + variables.SYNTHETIC_VARS
    )

    if MYSQL_VERSION_PARSED >= parse_version('5.6'):
        testable_metrics.extend(variables.PERFORMANCE_VARS)

    # Test metrics
    for mname in testable_metrics:
        # These two are currently not guaranteed outside of a Linux
        # environment.
        if mname == 'mysql.performance.user_time' and not Platform.is_linux():
            continue
        if mname == 'mysql.performance.kernel_time' and not Platform.is_linux():
            continue
        if mname == 'mysql.performance.cpu_time' and Platform.is_windows():
            continue

        if mname == 'mysql.performance.query_run_time.avg':
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:testdb'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:mysql'], count=1)
        elif mname == 'mysql.info.schema.size':
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:testdb'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:information_schema'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:performance_schema'], count=1)
        else:
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS, at_least=0)

    # TODO: test this if it is implemented
    # Assert service metadata
    # version_metadata = mysql_check.service_metadata['version']
    # assert len(version_metadata) == 1

    # test custom query metrics
    aggregator.assert_metric('alice.age', value=25)
    aggregator.assert_metric('bob.age', value=20)

    # test optional metrics
    optional_metrics = (
        variables.OPTIONAL_REPLICATION_METRICS
        + variables.OPTIONAL_INNODB_VARS
        + variables.OPTIONAL_STATUS_VARS
        + variables.OPTIONAL_STATUS_VARS_5_6_6
    )
    _test_optional_metrics(aggregator, optional_metrics, 1)

    # Raises when coverage < 100%
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connection_failure(aggregator, instance_error):
    """
    Service check reports connection failure
    """
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_error])

    with pytest.raises(Exception):
        mysql_check.check(instance_error)

    aggregator.assert_service_check('mysql.can_connect', status=MySql.CRITICAL, tags=tags.SC_FAILURE_TAGS, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_complex_config_replica(aggregator, instance_complex):
    config = copy.deepcopy(instance_complex)
    config['port'] = common.SLAVE_PORT
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[config])

    mysql_check.check(config)

    # self.assertMetricTag('mysql.replication.seconds_behind_master', 'channel:default')

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS_REPLICA, count=1)

    # Travis MySQL not running replication - FIX in flavored test.
    aggregator.assert_service_check(
        'mysql.replication.slave_running', status=MySql.OK, tags=tags.SC_TAGS_REPLICA, at_least=1
    )

    testable_metrics = (
        variables.STATUS_VARS
        + variables.VARIABLES_VARS
        + variables.INNODB_VARS
        + variables.BINLOG_VARS
        + variables.SYSTEM_METRICS
        + variables.SCHEMA_VARS
        + variables.SYNTHETIC_VARS
    )

    if MYSQL_VERSION_PARSED >= parse_version('5.6') and environ.get('MYSQL_FLAVOR') != 'mariadb':
        testable_metrics.extend(variables.PERFORMANCE_VARS)

    # Test metrics
    for mname in testable_metrics:
        # These two are currently not guaranteed outside of a Linux
        # environment.
        if mname == 'mysql.performance.user_time' and not Platform.is_linux():
            continue
        if mname == 'mysql.performance.kernel_time' and not Platform.is_linux():
            continue
        if mname == 'mysql.performance.cpu_time' and Platform.is_windows():
            continue
        if mname == 'mysql.performance.query_run_time.avg':
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:testdb'], at_least=1)
        elif mname == 'mysql.info.schema.size':
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:testdb'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:information_schema'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:performance_schema'], count=1)
        else:
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS, at_least=0)

    # test custom query metrics
    aggregator.assert_metric('alice.age', value=25)
    aggregator.assert_metric('bob.age', value=20)

    # test optional metrics
    optional_metrics = (
        variables.OPTIONAL_REPLICATION_METRICS
        + variables.OPTIONAL_INNODB_VARS
        + variables.OPTIONAL_STATUS_VARS
        + variables.OPTIONAL_STATUS_VARS_5_6_6
    )
    _test_optional_metrics(aggregator, optional_metrics, 1)

    # Raises when coverage < 100%
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_statement_metrics(aggregator, instance_complex):
    QUERY = 'select * from information_schema.processlist'
    QUERY_DIGEST_TEXT = 'SELECT * FROM `information_schema` . `processlist`'
    # The query signature should match the query and consistency of this tag has product impact. Do not change
    # the query signature for this test unless you know what you're doing. The query digest is determined by
    # mysql and varies across versions.
    QUERY_SIGNATURE = '8cd0f2b4343decc'
    if environ.get('MYSQL_FLAVOR') == 'mariadb':
        QUERY_DIGEST = '5d343195f2d7adf4388d42755311c3e3'
    elif environ.get('MYSQL_VERSION') == '5.6':
        QUERY_DIGEST = 'acfa199773950cd8cf912f3a19219492'
    elif environ.get('MYSQL_VERSION') == '5.7':
        QUERY_DIGEST = '0737e429dc883ba8c86c15ae76e59dda'
    else:
        # 8.0+
        QUERY_DIGEST = '6817a67871eb7edddad5b7836c93330aa3c98801ac759eed1bea6db1a34579c4'
        QUERY_SIGNATURE = '9d73cb71644af0a2'

    config = copy.deepcopy(instance_complex)
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[config])

    def run_query(q):
        with mysql_check._connect() as db:
            with closing(db.cursor()) as cursor:
                cursor.execute(q)

    # Run a query
    run_query(QUERY)
    mysql_check.check(config)

    # Run the query and check a second time so statement metrics are computed from the previous run
    run_query(QUERY)
    mysql_check.check(config)
    for name in statements.STATEMENT_METRICS.values():
        aggregator.assert_metric(
            name,
            tags=tags.SC_TAGS
            + [
                'query:{}'.format(QUERY_DIGEST_TEXT),
                'query_signature:{}'.format(QUERY_SIGNATURE),
                'digest:{}'.format(QUERY_DIGEST),
            ],
            count=1,
        )


def _test_optional_metrics(aggregator, optional_metrics, at_least):
    """
    Check optional metrics - there should be at least `at_least` matches
    """

    before = len(aggregator.not_asserted())

    for mname in optional_metrics:
        aggregator.assert_metric(mname, tags=tags.METRIC_TAGS, at_least=0)

    # Compute match rate
    after = len(aggregator.not_asserted())

    assert before - after > at_least


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
@pytest.mark.parametrize(
    'slave_io_running, slave_sql_running, check_status',
    [
        pytest.param({}, {}, MySql.CRITICAL),
        pytest.param({'stuff': 'yes'}, {}, MySql.WARNING),
        pytest.param({}, {'stuff': 'yes'}, MySql.WARNING),
        pytest.param({'stuff': 'yes'}, {'stuff': 'yes'}, MySql.OK),
    ],
)
def test_replication_check_status(slave_io_running, slave_sql_running, check_status, instance_basic, aggregator):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_basic])
    mysql_check.service_check_tags = ['foo:bar']
    mocked_results = {
        'Slaves_connected': 1,
        'Binlog_enabled': True,
        'Slave_IO_Running': slave_io_running,
        'Slave_SQL_Running': slave_sql_running,
    }

    mysql_check._check_replication_status(mocked_results)

    aggregator.assert_service_check('mysql.replication.slave_running', check_status, tags=['foo:bar'], count=1)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_version_metadata(instance_basic, datadog_agent, version_metadata):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_basic])
    mysql_check.check_id = 'test:123'

    mysql_check.check(instance_basic)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance_custom_queries, dd_run_check):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_custom_queries])
    dd_run_check(mysql_check)

    aggregator.assert_metric('alice.age', value=25, tags=tags.METRIC_TAGS)
    aggregator.assert_metric('bob.age', value=20, tags=tags.METRIC_TAGS)
