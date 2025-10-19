# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging

import mock
import pytest
from packaging.version import parse as parse_version

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.mysql import MySql
from datadog_checks.mysql.__about__ import __version__
from datadog_checks.mysql.const import (
    BINLOG_VARS,
    GALERA_VARS,
    GROUP_REPLICATION_VARS,
    GROUP_REPLICATION_VARS_8_0_2,
    INNODB_VARS,
    OPTIONAL_STATUS_VARS,
    OPTIONAL_STATUS_VARS_5_6_6,
    PERFORMANCE_VARS,
    REPLICA_VARS,
    SCHEMA_VARS,
    STATUS_VARS,
    SYNTHETIC_VARS,
    VARIABLES_VARS,
)

from . import common, tags, variables
from .common import HOST, MYSQL_FLAVOR, MYSQL_REPLICATION, MYSQL_VERSION_PARSED, PORT, requires_static_version


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_minimal_config(aggregator, dd_run_check, instance_basic):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    dd_run_check(mysql_check)

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS_MIN, count=1)

    # Test metrics
    testable_metrics = (
        variables.STATUS_VARS
        + variables.VARIABLES_VARS
        + variables.INNODB_VARS
        + variables.BINLOG_VARS
        + variables.COMMON_PERFORMANCE_VARS
        + variables.INDEX_SIZE_VARS
        + variables.INDEX_USAGE_VARS
        + [variables.OPERATION_TIME_METRIC_NAME]
    )

    if MYSQL_FLAVOR.lower() == 'mysql' and MYSQL_VERSION_PARSED < parse_version('5.7'):
        testable_metrics.extend(variables.INNODB_MUTEX_VARS)
    else:
        testable_metrics.extend(variables.INNODB_ROW_LOCK_VARS)

    operation_time_metrics = (
        variables.SIMPLE_OPERATION_TIME_METRICS + variables.COMMON_PERFORMANCE_OPERATION_TIME_METRICS
    )

    for mname in testable_metrics:
        # Adding condition to no longer test for innodb_os_log_fsyncs in mariadb 10.8+
        # (https://mariadb.com/kb/en/innodb-status-variables/#innodb_os_log_fsyncs)
        if (
            mname == 'mysql.innodb.os_log_fsyncs'
            and MYSQL_FLAVOR.lower() == 'mariadb'
            and MYSQL_VERSION_PARSED >= parse_version('10.8')
        ):
            continue
        else:
            aggregator.assert_metric(mname, at_least=1)

    optional_metrics = variables.SYSTEM_METRICS

    # Query cache and synthetic variables are not available in MySQL/Percona 8+
    if not (MYSQL_FLAVOR.lower() in ('mysql', 'percona') and MYSQL_VERSION_PARSED >= parse_version('8.0')):
        optional_metrics += variables.QCACHE_VARS

    _test_optional_metrics(aggregator, optional_metrics)

    _test_operation_time_metrics(aggregator, operation_time_metrics, mysql_check.debug_stats_kwargs()['tags'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), check_submission_type=True, exclude=[variables.OPERATION_TIME_METRIC_NAME]
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_complex_config(aggregator, dd_run_check, instance_complex):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_complex])
    dd_run_check(mysql_check)

    expected_metric_tags = tags.metrics_tags_with_resource(mysql_check)
    if (MYSQL_FLAVOR.lower() == 'mysql' and MYSQL_REPLICATION == 'classic') or MYSQL_FLAVOR.lower() == 'percona':
        expected_metric_tags += ('cluster_uuid:{}'.format(mysql_check.cluster_uuid), 'replication_role:primary')

    _assert_complex_config(
        aggregator,
        tags.SC_TAGS + tags.database_instance_resource_tags('stubbed.hostname'),
        expected_metric_tags,
    )
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        exclude=['alice.age', 'bob.age', variables.OPERATION_TIME_METRIC_NAME],
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_mysql_version_set(aggregator, dd_run_check, instance_basic):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    # run check twice to test the version is set once and only once
    dd_run_check(mysql_check, cancel=False)
    dd_run_check(mysql_check, cancel=True)
    assert mysql_check.version is not None
    assert mysql_check.tag_manager.get_tags().count('dbms_flavor:{}'.format(mysql_check.version.flavor.lower())) == 1


@pytest.mark.e2e
def test_e2e(dd_agent_check, dd_default_hostname, instance_complex, root_conn):
    aggregator = dd_agent_check(instance_complex, check_rate=True)

    expected_metric_tags = tags.METRIC_TAGS + (
        f'database_hostname:{dd_default_hostname}',
        f'database_instance:{dd_default_hostname}',
        'dbms_flavor:{}'.format(MYSQL_FLAVOR.lower()),
    )
    if MYSQL_FLAVOR in ('mysql', 'percona'):
        with root_conn.cursor() as cursor:
            cursor.execute("SELECT @@server_uuid")
            server_uuid = cursor.fetchone()[0]
            expected_metric_tags += ('server_uuid:{}'.format(server_uuid),)
            if MYSQL_REPLICATION == 'classic':
                expected_metric_tags += ('cluster_uuid:{}'.format(server_uuid), 'replication_role:primary')

    _assert_complex_config(
        aggregator,
        tags.SC_TAGS + tags.database_instance_resource_tags(dd_default_hostname),
        expected_metric_tags,
        hostname=dd_default_hostname,
        e2e=True,
    )
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=['alice.age', 'bob.age'] + variables.E2E_OPERATION_TIME_METRIC_NAME,
    )


def _assert_complex_config(
    aggregator, service_check_tags, metric_tags, hostname='stubbed.hostname', e2e=False, is_replica=False
):
    # Set replication mode once for reuse
    replication_mode = 'source' if not is_replica else 'replica'

    expected_counts = 2 if e2e else 1

    # Test service check
    aggregator.assert_service_check(
        'mysql.can_connect',
        status=MySql.OK,
        tags=service_check_tags,
        hostname=hostname,
        count=1,
    )
    if MYSQL_REPLICATION == 'classic':
        aggregator.assert_service_check(
            'mysql.replication.slave_running',
            status=MySql.OK,
            tags=service_check_tags + (f'replication_mode:{replication_mode}',),
            hostname=hostname,
            at_least=1,
        )
    testable_metrics = (
        variables.STATUS_VARS
        + variables.VARIABLES_VARS
        + variables.INNODB_VARS
        + variables.BINLOG_VARS
        + variables.SCHEMA_VARS
        + variables.TABLE_VARS
    )

    if MYSQL_FLAVOR.lower() in ('mariadb', 'percona'):
        testable_metrics.extend(variables.ROW_TABLE_STATS_VARS)

    # Query cache and synthetic variables are not available in MySQL/Percona 8+
    if not (MYSQL_FLAVOR.lower() in ('mysql', 'percona') and MYSQL_VERSION_PARSED >= parse_version('8.0')):
        testable_metrics.extend(variables.QCACHE_VARS)

    if MYSQL_FLAVOR.lower() == 'mysql' and MYSQL_VERSION_PARSED < parse_version('5.7'):
        testable_metrics.extend(variables.INNODB_MUTEX_VARS)
    else:
        testable_metrics.extend(variables.INNODB_ROW_LOCK_VARS)

    operation_time_metrics = variables.SIMPLE_OPERATION_TIME_METRICS + variables.COMPLEX_OPERATION_TIME_METRICS

    if MYSQL_REPLICATION == 'group':
        testable_metrics.extend(variables.GROUP_REPLICATION_VARS)
        group_replication_tags = ('channel_name:group_replication_applier', 'member_state:ONLINE')
        if MYSQL_VERSION_PARSED >= parse_version('8.0'):
            testable_metrics.extend(variables.GROUP_REPLICATION_VARS_8_0_2)
            group_replication_tags += ('member_role:PRIMARY',)
        aggregator.assert_service_check(
            'mysql.replication.group.status',
            status=MySql.OK,
            tags=service_check_tags + group_replication_tags,
            count=1,
        )
        operation_time_metrics.extend(variables.GROUP_REPLICATION_OPERATION_TIME_METRICS)
    else:
        operation_time_metrics.extend(variables.REPLICATION_OPERATION_TIME_METRICS)

    if MYSQL_VERSION_PARSED >= parse_version('5.6'):
        testable_metrics.extend(variables.PERFORMANCE_VARS + variables.COMMON_PERFORMANCE_VARS)
        operation_time_metrics.extend(
            variables.COMMON_PERFORMANCE_OPERATION_TIME_METRICS + variables.PERFORMANCE_OPERATION_TIME_METRICS
        )

    # Test metrics
    for mname in testable_metrics:
        # Adding condition to no longer test for innodb_os_log_fsyncs in mariadb 10.8+
        # (https://mariadb.com/kb/en/innodb-status-variables/#innodb_os_log_fsyncs)
        if (
            mname == 'mysql.innodb.os_log_fsyncs'
            and MYSQL_FLAVOR.lower() == 'mariadb'
            and MYSQL_VERSION_PARSED >= parse_version('10.8')
        ):
            continue
        if mname == 'mysql.performance.query_run_time.avg':
            aggregator.assert_metric(mname, tags=metric_tags + ('schema:testdb',), count=expected_counts)
            if not is_replica:
                aggregator.assert_metric(mname, tags=metric_tags + ('schema:mysql',), count=expected_counts)
        elif mname == 'mysql.info.schema.size':
            aggregator.assert_metric(mname, tags=metric_tags + ('schema:testdb',), count=expected_counts)
            if not is_replica:
                aggregator.assert_metric(
                    mname, tags=metric_tags + ('schema:information_schema',), count=expected_counts
                )
                aggregator.assert_metric(
                    mname, tags=metric_tags + ('schema:performance_schema',), count=expected_counts
                )
        elif mname in variables.TABLE_VARS:
            aggregator.assert_metric(
                mname,
                tags=metric_tags
                + (
                    'schema:testdb',
                    'table:users',
                ),
                count=expected_counts,
            )
            if not is_replica:
                aggregator.assert_metric(
                    mname,
                    tags=metric_tags
                    + (
                        'schema:information_schema',
                        'table:VIEWS',
                    ),
                    count=expected_counts,
                )
                aggregator.assert_metric(
                    mname,
                    tags=metric_tags
                    + (
                        'schema:performance_schema',
                        'table:users',
                    ),
                    count=expected_counts,
                )
        elif mname == 'mysql.replication.slave_running':
            aggregator.assert_metric(
                mname, tags=metric_tags + (f'replication_mode:{replication_mode}',), count=expected_counts
            )
        elif mname == 'mysql.performance.user_connections':
            if MYSQL_FLAVOR.lower() in ('mysql', 'percona') and MYSQL_VERSION_PARSED >= parse_version('8.0'):
                processlist_state = "executing"
            else:
                processlist_state = "Sending data"
            aggregator.assert_metric(
                mname,
                tags=metric_tags
                + (
                    'processlist_state:{}'.format(processlist_state),
                    'processlist_user:dog',
                    'processlist_db:None',
                ),
                at_least=0,  # TODO this metric includes processlist_host tag which contains a random IP address
            )
        elif mname == 'mysql.replication.group.member_status':
            aggregator.assert_metric(mname, tags=metric_tags + group_replication_tags, count=expected_counts)
        elif mname in variables.GROUP_REPLICATION_VARS + variables.GROUP_REPLICATION_VARS_8_0_2:
            aggregator.assert_metric(
                mname, tags=metric_tags + ('channel_name:group_replication_applier',), count=expected_counts
            )
        elif mname in variables.ROW_TABLE_STATS_VARS:
            aggregator.assert_metric(
                mname,
                tags=metric_tags
                + (
                    'schema:testdb',
                    'table:users',
                ),
                at_least=1,
            )
        elif mname == 'mysql.performance.qcache.utilization.instant':
            # This metric will only be collected if query_cache_type is enabled and on a second check run
            aggregator.assert_metric(mname, tags=metric_tags, at_least=0)
        else:
            aggregator.assert_metric(mname, tags=metric_tags, at_least=1)

    # TODO: test this if it is implemented
    # Assert service metadata
    # version_metadata = mysql_check.service_metadata['version']
    # assert len(version_metadata) == 1

    # test custom query metrics
    aggregator.assert_metric('alice.age', value=25)
    aggregator.assert_metric('bob.age', value=20)

    _test_index_metrics(aggregator, variables.INDEX_USAGE_VARS + variables.INDEX_SIZE_VARS, metric_tags)
    # test optional metrics
    optional_metrics = (
        variables.OPTIONAL_REPLICATION_METRICS
        + variables.OPTIONAL_INNODB_VARS
        + variables.OPTIONAL_STATUS_VARS
        + variables.OPTIONAL_STATUS_VARS_5_6_6
        + variables.SYSTEM_METRICS  # Can only be collected when Postgres is running locally to tests
    )
    # Note, this assertion will pass even if some metrics are not present.
    # Manual testing is required for optional metrics
    _test_optional_metrics(aggregator, optional_metrics)

    _test_operation_time_metrics(
        aggregator, operation_time_metrics, metric_tags + ('agent_hostname:{}'.format(hostname),), e2e=e2e
    )

    # Raises when coverage < 100%
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connection_failure(aggregator, dd_run_check, instance_error):
    """
    Service check reports connection failure
    """
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_error])

    with pytest.raises(Exception):
        dd_run_check(mysql_check)

    aggregator.assert_service_check('mysql.can_connect', status=MySql.CRITICAL, tags=tags.SC_FAILURE_TAGS, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@common.requires_classic_replication
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_complex_config_replica(aggregator, dd_run_check, instance_complex):
    config = copy.deepcopy(instance_complex)
    config['port'] = common.SLAVE_PORT
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[config])

    dd_run_check(mysql_check)

    expected_metric_tags = tags.metrics_tags_with_resource(mysql_check)
    if MYSQL_FLAVOR.lower() in ('mysql', 'percona') and MYSQL_REPLICATION == 'classic':
        expected_metric_tags += ("cluster_uuid:{}".format(mysql_check.cluster_uuid), "replication_role:replica")
        assert mysql_check.server_uuid != mysql_check.cluster_uuid, (
            "Server UUID and cluster UUID should not be the same for replica"
        )

    _assert_complex_config(
        aggregator,
        tags.SC_TAGS_REPLICA,
        expected_metric_tags,
        is_replica=True,
    )
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        exclude=['alice.age', 'bob.age', variables.OPERATION_TIME_METRIC_NAME],
    )

    # Make sure group replication is not detected
    with mysql_check._connect() as db:
        assert mysql_check._is_group_replication_active(db) is False


@pytest.mark.integration
@pytest.mark.parametrize(
    'dbm_enabled, reported_hostname, expected_hostname',
    [
        (True, '', 'resolved.hostname'),
        (False, '', 'resolved.hostname'),
        (False, 'forced_hostname', 'forced_hostname'),
        (True, 'forced_hostname', 'forced_hostname'),
    ],
)
def test_correct_hostname(dbm_enabled, reported_hostname, expected_hostname, aggregator, dd_run_check, instance_basic):
    instance_basic['dbm'] = dbm_enabled
    if dbm_enabled:
        # set a very small collection interval so the tests go fast
        instance_basic['collect_settings'] = {'collection_interval': 0.1}
        instance_basic['query_activity'] = {'collection_interval': 0.1}
        instance_basic['query_samples'] = {'collection_interval': 0.1}
        instance_basic['query_metrics'] = {'collection_interval': 0.1}
    instance_basic['disable_generic_tags'] = False  # This flag also affects the hostname
    instance_basic['reported_hostname'] = reported_hostname

    with mock.patch('datadog_checks.mysql.MySql.resolve_db_host', return_value='resolved.hostname') as resolve_db_host:
        mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
        dd_run_check(mysql_check)
        assert resolve_db_host.called is True

    expected_tags = (
        'database_hostname:{}'.format(mysql_check.database_hostname),
        'database_instance:{}'.format(expected_hostname),
        'server:{}'.format(HOST),
        'port:{}'.format(PORT),
        'dd.internal.resource:database_instance:{}'.format(expected_hostname),
    )
    aggregator.assert_service_check(
        'mysql.can_connect', status=MySql.OK, tags=expected_tags, count=1, hostname=expected_hostname
    )

    testable_metrics = variables.STATUS_VARS + variables.VARIABLES_VARS + variables.INNODB_VARS + variables.BINLOG_VARS

    if MYSQL_FLAVOR.lower() == 'mysql' and MYSQL_VERSION_PARSED < parse_version('5.7'):
        testable_metrics.extend(variables.INNODB_MUTEX_VARS)
    else:
        testable_metrics.extend(variables.INNODB_ROW_LOCK_VARS)

    for mname in testable_metrics:
        # Adding condition to no longer test for innodb_os_log_fsyncs in mariadb 10.8+
        # (https://mariadb.com/kb/en/innodb-status-variables/#innodb_os_log_fsyncs)
        if (
            mname == 'mysql.innodb.os_log_fsyncs'
            and MYSQL_FLAVOR.lower() == 'mariadb'
            and MYSQL_VERSION_PARSED >= parse_version('10.8')
        ):
            continue
        aggregator.assert_metric(mname, hostname=expected_hostname, count=1)

    optional_metrics = (
        variables.SYSTEM_METRICS  # Can only be collected when Postgres is running locally to tests
    )

    # Query cache and synthetic variables are not available in MySQL/Percona 8+
    if not (MYSQL_FLAVOR.lower() in ('mysql', 'percona') and MYSQL_VERSION_PARSED >= parse_version('8.0')):
        optional_metrics += variables.QCACHE_VARS

    for mname in optional_metrics:
        aggregator.assert_metric(mname, hostname=expected_hostname, at_least=0)


def _test_index_metrics(aggregator, index_metrics, metric_tags):
    for mname in index_metrics:
        if mname in ['mysql.index.reads', 'mysql.index.updates', 'mysql.index.deletes']:
            aggregator.assert_metric(
                mname,
                tags=metric_tags + ('db:testdb', 'table:users', 'index:id'),
                count=1,
            )
            aggregator.assert_metric(
                mname,
                tags=metric_tags
                + (
                    'db:datadog_test_schemas',
                    'table:cities',
                    'index:single_column_index',
                ),
                count=1,
            )
            aggregator.assert_metric(
                mname,
                tags=metric_tags + ('db:datadog_test_schemas', 'table:cities', 'index:two_columns_index'),
                count=1,
            )
        if mname == 'mysql.index.size':
            aggregator.assert_metric(mname, tags=metric_tags + ('db:testdb', 'table:users', 'index:id'), count=1)
            aggregator.assert_metric(
                mname,
                tags=metric_tags + ('db:datadog_test_schemas', 'table:cities', 'index:single_column_index'),
                count=1,
            )
            aggregator.assert_metric(
                mname,
                tags=metric_tags + ('db:datadog_test_schemas', 'table:cities', 'index:two_columns_index'),
                count=1,
            )


def _test_optional_metrics(aggregator, optional_metrics):
    """
    Check optional metrics - They can either be present or not
    """

    before = len(aggregator.not_asserted())

    # If there are no metrics to assert, return early
    if before == 0:
        return

    for mname in optional_metrics:
        aggregator.assert_metric(mname, tags=tags.METRIC_TAGS_WITH_RESOURCE, at_least=0)

    # Compute match rate
    after = len(aggregator.not_asserted())

    assert before > after, aggregator.not_asserted()


def _test_operation_time_metrics(aggregator, operation_time_metrics, tags, e2e=False):
    for operation_time_metric in operation_time_metrics:
        if e2e:
            for metric_name in variables.E2E_OPERATION_TIME_METRIC_NAME:
                aggregator.assert_metric(
                    metric_name,
                    tags=list(tags) + ['operation:{}'.format(operation_time_metric)],
                    count=2,
                )
        else:
            aggregator.assert_metric(
                variables.OPERATION_TIME_METRIC_NAME,
                tags=list(tags) + ['operation:{}'.format(operation_time_metric)],
                count=1,
            )


@requires_static_version
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_version_metadata(dd_run_check, instance_basic, datadog_agent, version_metadata):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    mysql_check.check_id = 'test:123'

    dd_run_check(mysql_check)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance_custom_queries, dd_run_check):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_custom_queries])
    dd_run_check(mysql_check)

    aggregator.assert_metric('alice.age', value=25, tags=tags.metrics_tags_with_resource(mysql_check))
    aggregator.assert_metric('bob.age', value=20, tags=tags.metrics_tags_with_resource(mysql_check))


@pytest.mark.usefixtures('dd_environment')
def test_only_custom_queries(aggregator, dd_run_check, instance_custom_queries):
    instance_custom_queries['only_custom_queries'] = True
    check = MySql(common.CHECK_NAME, {}, [instance_custom_queries])
    dd_run_check(check)

    standard_metric_sets = [
        STATUS_VARS,
        VARIABLES_VARS,
        INNODB_VARS,
        BINLOG_VARS,
        OPTIONAL_STATUS_VARS,
        OPTIONAL_STATUS_VARS_5_6_6,
        GALERA_VARS,
        PERFORMANCE_VARS,
        SCHEMA_VARS,
        SYNTHETIC_VARS,
        REPLICA_VARS,
        GROUP_REPLICATION_VARS,
        variables.QUERY_EXECUTOR_METRIC_SETS,
    ]

    if MYSQL_VERSION_PARSED >= parse_version('8.0.2'):
        standard_metric_sets.append(GROUP_REPLICATION_VARS_8_0_2)

    for metric_set in standard_metric_sets:
        for metric_def in metric_set.values():
            metric = metric_def[0]
            aggregator.assert_metric(metric, count=0)

    # Internal check metrics are still allowed even if only_custom_queries is enabled
    internal_metrics = [m for m in aggregator.metric_names if m.startswith('dd.')]
    for m in internal_metrics:
        aggregator.assert_metric(m, at_least=0)

    aggregator.assert_metric('alice.age', value=25, tags=tags.metrics_tags_with_resource(check))
    aggregator.assert_metric('bob.age', value=20, tags=tags.metrics_tags_with_resource(check))
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_additional_status(aggregator, dd_run_check, instance_additional_status):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_additional_status])
    dd_run_check(mysql_check)

    # MariaDB 10.10 seems to take out the information that we use for gathering this metric if they're at 0
    # Removing this from the test (the metric is optional) for the time being
    if (
        MYSQL_FLAVOR.lower() == 'mariadb' and MYSQL_VERSION_PARSED < parse_version('10.10')
    ) or MYSQL_FLAVOR.lower() == 'mysql':
        aggregator.assert_metric(
            'mysql.innodb.rows_read', metric_type=1, tags=tags.metrics_tags_with_resource(mysql_check)
        )
    aggregator.assert_metric(
        'mysql.innodb.row_lock_time', metric_type=1, tags=tags.metrics_tags_with_resource(mysql_check)
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_additional_variable(aggregator, dd_run_check, instance_additional_variable):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_additional_variable])
    dd_run_check(mysql_check)

    aggregator.assert_metric(
        'mysql.performance.long_query_time', metric_type=0, tags=tags.metrics_tags_with_resource(mysql_check)
    )
    aggregator.assert_metric(
        'mysql.performance.innodb_flush_log_at_trx_commit',
        metric_type=0,
        tags=tags.metrics_tags_with_resource(mysql_check),
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_additional_variable_unknown(aggregator, dd_run_check, instance_invalid_var):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_invalid_var])
    dd_run_check(mysql_check)

    aggregator.assert_metric(
        'mysql.performance.longer_query_time', metric_type=0, tags=tags.metrics_tags_with_resource(mysql_check), count=0
    )
    aggregator.assert_metric(
        'mysql.performance.innodb_flush_log_at_trx_commit',
        metric_type=0,
        tags=tags.metrics_tags_with_resource(mysql_check),
        count=1,
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_additional_status_already_queried(aggregator, dd_run_check, instance_status_already_queried, caplog):
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_status_already_queried])
    dd_run_check(mysql_check)

    aggregator.assert_metric(
        'mysql.performance.open_files_test', metric_type=0, tags=tags.metrics_tags_with_resource(mysql_check), count=0
    )
    aggregator.assert_metric(
        'mysql.performance.open_files', metric_type=0, tags=tags.metrics_tags_with_resource(mysql_check), count=1
    )

    assert (
        "Skipping status variable Open_files for metric mysql.performance.open_files_test as "
        "it is already collected by mysql.performance.open_files" in caplog.text
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_additional_var_already_queried(aggregator, dd_run_check, instance_var_already_queried, caplog):
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_var_already_queried])
    dd_run_check(mysql_check)

    aggregator.assert_metric(
        'mysql.myisam.key_buffer_size', metric_type=0, tags=tags.metrics_tags_with_resource(mysql_check), count=1
    )

    assert (
        "Skipping variable Key_buffer_size for metric mysql.myisam.key_buffer_size as "
        "it is already collected by mysql.myisam.key_buffer_size" in caplog.text
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "cloud_metadata,metric_names",
    [
        (
            {},
            [],
        ),
        (
            {
                'azure': {
                    'deployment_type': 'flexible_server',
                    'name': 'my-instance',
                },
            },
            ["dd.internal.resource:azure_mysql_flexible_server:my-instance"],
        ),
        (
            {
                'azure': {
                    'deployment_type': 'virtual_machine',
                    'name': 'my-instance',
                },
            },
            ["dd.internal.resource:azure_virtual_machine_instance:my-instance"],
        ),
        (
            {
                'aws': {
                    'instance_endpoint': 'foo.aws.com',
                },
            },
            [
                "dd.internal.resource:aws_rds_instance:foo.aws.com",
            ],
        ),
        (
            {
                'gcp': {
                    'project_id': 'foo-project',
                    'instance_id': 'bar',
                    'extra_field': 'included',
                },
            },
            [
                "dd.internal.resource:gcp_sql_database_instance:foo-project:bar",
            ],
        ),
        (
            {
                'aws': {
                    'instance_endpoint': 'foo.aws.com',
                },
                'azure': {
                    'deployment_type': 'single_server',
                    'name': 'my-instance',
                },
            },
            [
                "dd.internal.resource:aws_rds_instance:foo.aws.com",
                "dd.internal.resource:azure_mysql_server:my-instance",
            ],
        ),
    ],
)
def test_set_resources(aggregator, dd_run_check, instance_basic, cloud_metadata, metric_names):
    if cloud_metadata:
        for k, v in cloud_metadata.items():
            instance_basic[k] = v
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    dd_run_check(mysql_check)
    for m in metric_names:
        aggregator.assert_metric_has_tag("mysql.net.connections", m)
    aggregator.assert_metric_has_tag(
        "mysql.net.connections",
        f'dd.internal.resource:database_instance:{mysql_check.resolved_hostname}',
    )


@pytest.mark.parametrize(
    'dbm_enabled, reported_hostname',
    [
        (True, None),
        (False, None),
        (True, 'forced_hostname'),
        (False, 'forced_hostname'),
    ],
)
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_database_instance_metadata(aggregator, dd_run_check, instance_complex, dbm_enabled, reported_hostname):
    instance_complex['dbm'] = dbm_enabled
    if dbm_enabled:
        # set a very small collection interval so the tests go fast
        instance_complex['collect_settings'] = {'collection_interval': 0.1}
        instance_complex['query_activity'] = {'collection_interval': 0.1}
        instance_complex['query_samples'] = {'collection_interval': 0.1}
        instance_complex['query_metrics'] = {'collection_interval': 0.1}

    expected_host = expected_database_hostname = expected_database_instance = "stubbed.hostname"
    if reported_hostname:
        instance_complex['reported_hostname'] = reported_hostname
        expected_host = reported_hostname
        expected_database_instance = reported_hostname

    expected_tags = tags.METRIC_TAGS + (
        "database_hostname:{}".format(expected_database_hostname),
        "database_instance:{}".format(expected_database_instance),
        'dd.internal.resource:database_instance:{}'.format(expected_database_instance),
        "dbms_flavor:{}".format(MYSQL_FLAVOR.lower()),
    )

    mysql_check = MySql(common.CHECK_NAME, {}, [instance_complex])
    dd_run_check(mysql_check)

    if MYSQL_FLAVOR.lower() in ('mysql', 'percona'):
        expected_tags += ("server_uuid:{}".format(mysql_check.server_uuid),)
        if MYSQL_REPLICATION == 'classic':
            expected_tags += ('cluster_uuid:{}'.format(mysql_check.cluster_uuid), 'replication_role:primary')

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'database_instance'), None)

    assert event is not None
    assert event['host'] == expected_host
    assert event['database_instance'] == expected_database_instance
    assert event['database_hostname'] == expected_database_hostname
    assert event['dbms'] == "mysql"
    assert event['ddagenthostname'] == "stubbed.hostname"
    assert sorted(event['tags']) == sorted(expected_tags)
    assert event['integration_version'] == __version__
    assert event['collection_interval'] == 300
    assert event['metadata'] == {
        'dbm': dbm_enabled,
        'connection_host': instance_complex['host'],
    }

    # Run a second time and expect the metadata to not be emitted again because of the cache TTL
    aggregator.reset()
    dd_run_check(mysql_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'database_instance'), None)
    assert event is None


@pytest.mark.parametrize(
    'instance_propagate_agent_tags,init_config_propagate_agent_tags,should_propagate_agent_tags',
    [
        pytest.param(True, True, True, id="both true"),
        pytest.param(True, False, True, id="instance config true prevails"),
        pytest.param(False, True, False, id="instance config false prevails"),
        pytest.param(False, False, False, id="both false"),
        pytest.param(None, True, True, id="init_config true applies to all instances"),
        pytest.param(None, False, False, id="init_config false applies to all instances"),
        pytest.param(None, None, False, id="default to false"),
        pytest.param(True, None, True, id="instance config true prevails, init_config is None"),
        pytest.param(False, None, False, id="instance config false prevails, init_config is None"),
    ],
)
@pytest.mark.integration
def test_propagate_agent_tags(
    aggregator,
    dd_run_check,
    instance_basic,
    instance_propagate_agent_tags,
    init_config_propagate_agent_tags,
    should_propagate_agent_tags,
):
    instance_basic['propagate_agent_tags'] = instance_propagate_agent_tags
    init_config = {}
    if init_config_propagate_agent_tags is not None:
        init_config['propagate_agent_tags'] = init_config_propagate_agent_tags

    agent_tags = ('my-env:test-env', 'random:tag', 'bar:foo')
    expected_tags = (
        instance_basic.get('tags', ())
        + (
            'database_hostname:stubbed.hostname',
            'database_instance:forced_hostname',
            'server:{}'.format(HOST),
            'port:{}'.format(PORT),
            'dd.internal.resource:database_instance:forced_hostname',
            "dd.internal.resource:aws_rds_instance:foo.aws.com",
            "dd.internal.resource:azure_mysql_server:my-instance",
            'dd.internal.resource:gcp_sql_database_instance:foo-project:bar',
        )
        + agent_tags
    )

    with mock.patch('datadog_checks.mysql.config.get_agent_host_tags', return_value=agent_tags):
        check = MySql(common.CHECK_NAME, init_config, [instance_basic])
        assert check._config._should_propagate_agent_tags(instance_basic, init_config) == should_propagate_agent_tags
        if should_propagate_agent_tags:
            assert all(tag in check.tag_manager.get_tags() for tag in agent_tags)
            dd_run_check(check)
            aggregator.assert_service_check(
                'mysql.can_connect',
                count=1,
                status=MySql.OK,
                tags=expected_tags,
            )
