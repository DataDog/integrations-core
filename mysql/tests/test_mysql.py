# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from os import environ

import pytest
from pkg_resources import parse_version

from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.mysql import MySql
from tests.conftest import MYSQL_VERSION

from . import common, tags, variables
from .common import MYSQL_VERSION_PARSED


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_minimal_config(aggregator, dd_run_check, instance_basic):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    dd_run_check(mysql_check)

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS_MIN, count=1)

    # Test metrics
    testable_metrics = variables.STATUS_VARS + variables.VARIABLES_VARS + variables.INNODB_VARS + variables.BINLOG_VARS

    for mname in testable_metrics:
        aggregator.assert_metric(mname, at_least=1)

    optional_metrics = (
        variables.COMPLEX_STATUS_VARS
        + variables.COMPLEX_VARIABLES_VARS
        + variables.COMPLEX_INNODB_VARS
        + variables.SYSTEM_METRICS
        + variables.SYNTHETIC_VARS
    )

    _test_optional_metrics(aggregator, optional_metrics)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_complex_config(aggregator, dd_run_check, instance_complex):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_complex])
    dd_run_check(mysql_check)

    _assert_complex_config(aggregator)
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), check_submission_type=True, exclude=['alice.age', 'bob.age'] + variables.STATEMENT_VARS
    )


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance_complex):
    aggregator = dd_agent_check(instance_complex)
    _assert_complex_config(aggregator, hostname=None)  # Do not assert hostname
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), exclude=['alice.age', 'bob.age'] + variables.STATEMENT_VARS
    )


def _assert_complex_config(aggregator, hostname='stubbed.hostname'):
    # Test service check
    aggregator.assert_service_check(
        'mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS, hostname=hostname, count=1
    )
    aggregator.assert_service_check(
        'mysql.replication.slave_running',
        status=MySql.OK,
        tags=tags.SC_TAGS + ['replication_mode:source'],
        hostname='stubbed.hostname',
        at_least=1,
    )
    testable_metrics = (
        variables.STATUS_VARS
        + variables.COMPLEX_STATUS_VARS
        + variables.VARIABLES_VARS
        + variables.COMPLEX_VARIABLES_VARS
        + variables.INNODB_VARS
        + variables.COMPLEX_INNODB_VARS
        + variables.BINLOG_VARS
        + variables.SYSTEM_METRICS
        + variables.SCHEMA_VARS
        + variables.SYNTHETIC_VARS
        + variables.STATEMENT_VARS
    )

    if MYSQL_VERSION_PARSED >= parse_version('5.6'):
        testable_metrics.extend(variables.PERFORMANCE_VARS)

    # Test metrics
    for mname in testable_metrics:
        # These three are currently not guaranteed outside of a Linux
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
    # Note, this assertion will pass even if some metrics are not present.
    # Manual testing is required for optional metrics
    _test_optional_metrics(aggregator, optional_metrics)

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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_complex_config_replica(aggregator, dd_run_check, instance_complex):
    config = copy.deepcopy(instance_complex)
    config['port'] = common.SLAVE_PORT
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[config])

    dd_run_check(mysql_check)

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS_REPLICA, count=1)

    # Travis MySQL not running replication - FIX in flavored test.
    aggregator.assert_service_check(
        'mysql.replication.slave_running',
        status=MySql.OK,
        tags=tags.SC_TAGS_REPLICA + ['replication_mode:replica'],
        at_least=1,
    )

    testable_metrics = (
        variables.STATUS_VARS
        + variables.COMPLEX_STATUS_VARS
        + variables.VARIABLES_VARS
        + variables.COMPLEX_VARIABLES_VARS
        + variables.INNODB_VARS
        + variables.COMPLEX_INNODB_VARS
        + variables.BINLOG_VARS
        + variables.SYSTEM_METRICS
        + variables.SCHEMA_VARS
        + variables.SYNTHETIC_VARS
        + variables.STATEMENT_VARS
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
    # Note, this assertion will pass even if some metrics are not present.
    # Manual testing is required for optional metrics
    _test_optional_metrics(aggregator, optional_metrics)

    # Raises when coverage < 100%
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), check_submission_type=True, exclude=['alice.age', 'bob.age'] + variables.STATEMENT_VARS
    )


@pytest.mark.parametrize('dbm_enabled', (True, False))
def test_correct_hostname(dbm_enabled, aggregator, dd_run_check, instance_basic):
    instance_basic['dbm'] = dbm_enabled
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    dd_run_check(mysql_check)

    expected_hostname = 'stubbed.hostname' if dbm_enabled else None

    aggregator.assert_service_check(
        'mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS_MIN, count=1, hostname=expected_hostname
    )

    testable_metrics = variables.STATUS_VARS + variables.VARIABLES_VARS + variables.INNODB_VARS + variables.BINLOG_VARS
    for metric_name in testable_metrics:
        aggregator.assert_metric(metric_name, hostname=expected_hostname)

    optional_metrics = (
        variables.COMPLEX_STATUS_VARS
        + variables.COMPLEX_VARIABLES_VARS
        + variables.COMPLEX_INNODB_VARS
        + variables.SYSTEM_METRICS
        + variables.SYNTHETIC_VARS
    )

    for metric_name in optional_metrics:
        aggregator.assert_metric(metric_name, hostname=expected_hostname, at_least=0)


def _test_optional_metrics(aggregator, optional_metrics):
    """
    Check optional metrics - They can either be present or not
    """

    before = len(aggregator.not_asserted())

    for mname in optional_metrics:
        aggregator.assert_metric(mname, tags=tags.METRIC_TAGS, at_least=0)

    # Compute match rate
    after = len(aggregator.not_asserted())

    assert before > after


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

    aggregator.assert_metric('alice.age', value=25, tags=tags.METRIC_TAGS)
    aggregator.assert_metric('bob.age', value=20, tags=tags.METRIC_TAGS)
