# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.mysql import MySql
from datadog_checks.utils.platform import Platform

import common
import variables


def test_check(aggregator, spin_up_mysql):
    assert True


def test_minimal_config(aggregator, spin_up_mysql):
    mysql_check = MySql(common.CHECK_NAME, {}, {})
    mysql_check.check(common.MYSQL_MINIMAL_CONFIG)

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK,
        tags=variables.SC_TAGS_MIN, count=1)

    # Test metrics
    testable_metrics = (variables.STATUS_VARS + variables.VARIABLES_VARS + variables.INNODB_VARS +
                        variables.BINLOG_VARS + variables.SYSTEM_METRICS + variables.SYNTHETIC_VARS)

    for mname in testable_metrics:
        aggregator.assert_metric(mname, at_least=0)


def test_complex_config(aggregator, spin_up_mysql):
    mysql_check = MySql(common.CHECK_NAME, {}, {}, instances=[common.MYSQL_COMPLEX_CONFIG])
    mysql_check.check(common.MYSQL_COMPLEX_CONFIG)

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK,
        tags=variables.SC_TAGS, count=1)

    aggregator.assert_service_check('mysql.replication.slave_running', status=MySql.OK,
        tags=variables.SC_TAGS, at_least=1)

    ver = map(lambda x: int(x), mysql_check.service_metadata[0]['version'].split("."))
    ver = tuple(ver)

    testable_metrics = (variables.STATUS_VARS + variables.VARIABLES_VARS +
                        variables.INNODB_VARS + variables.BINLOG_VARS +
                        variables.SYSTEM_METRICS + variables.SCHEMA_VARS +
                        variables.SYNTHETIC_VARS)

    if ver >= (5, 6, 0) and environ.get('MYSQL_FLAVOR') != 'mariadb':
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
            aggregator.assert_metric(mname,
                tags=variables.METRIC_TAGS+['schema:testdb'],
                count=1)
            aggregator.assert_metric(mname,
                tags=variables.METRIC_TAGS+['schema:mysql'],
                count=1)
        elif mname == 'mysql.info.schema.size':
            aggregator.assert_metric(mname,
                tags=variables.METRIC_TAGS+['schema:testdb'],
                count=1)
            aggregator.assert_metric(mname,
                tags=variables.METRIC_TAGS+['schema:information_schema'],
                count=1)
            aggregator.assert_metric(mname,
                tags=variables.METRIC_TAGS+['schema:performance_schema'],
                count=1)
        else:
            aggregator.assert_metric(mname,
            tags=variables.METRIC_TAGS,
            at_least=0)

    # Assert service metadata
    version_metadata = mysql_check.service_metadata['version']
    assert len(version_metadata) == 1

    # test custom query metrics
    aggregator.assert_metric('alice.age', value=25)
    aggregator.assert_metric('bob.age', value=20)

    # test optional metrics
    optional_metrics = (variables.OPTIONAL_REPLICATION_METRICS +
        variables.OPTIONAL_INNODB_VARS +
        variables.OPTIONAL_STATUS_VARS +
        variables.OPTIONAL_STATUS_VARS_5_6_6)
    _test_optional_metrics(aggregator, optional_metrics, 1)

    # Raises when coverage < 100%
    aggregator.assert_all_metrics_covered()


def test_connection_failure(aggregator, spin_up_mysql):
    """
    Service check reports connection failure
    """
    mysql_check = MySql(common.CHECK_NAME, {}, {}, instances=[common.MYSQL_COMPLEX_CONFIG])
    mysql_check.check(common.MYSQL_COMPLEX_CONFIG)

    with pytest.raises(Exception):
        mysql_check.check(config)

    aggregator.assert_service_check('mysql.can_connect', status=MySql.CRITICAL,
        tags=variables.SC_FAILURE_TAGS, count=1)

    aggregator.assert_all_metrics_covered()



# def test_complex_config_replica(self):
#     config = {'instances': self.MYSQL_COMPLEX_CONFIG}
#     config['instances'][0]['port'] = 13307
#     self.run_check_twice(config)
#
#     self.assertMetricTag('mysql.replication.seconds_behind_master', 'channel:default')
#
#     # Test service check
#     self.assertServiceCheck('mysql.can_connect', status=AgentCheck.OK,
#                             tags=self.SC_TAGS_REPLICA, count=1)
#
#     # Travis MySQL not running replication - FIX in flavored test.
#     self.assertServiceCheck('mysql.replication.slave_running', status=AgentCheck.OK,
#                             tags=self.SC_TAGS_REPLICA, at_least=1)
#
#     ver = map(lambda x: int(x), self.service_metadata[0]['version'].split("."))
#     ver = tuple(ver)
#
#     testable_metrics = (self.STATUS_VARS + self.VARIABLES_VARS + self.INNODB_VARS +
#                         self.BINLOG_VARS + self.SYSTEM_METRICS + self.SCHEMA_VARS + self.SYNTHETIC_VARS)
#
#     if ver >= (5, 6, 0) and environ.get('MYSQL_FLAVOR') != 'mariadb':
#         testable_metrics.extend(self.PERFORMANCE_VARS)
#
#     # Test metrics
#     for mname in testable_metrics:
#         # These two are currently not guaranteed outside of a Linux
#         # environment.
#         if mname == 'mysql.performance.user_time' and not Platform.is_linux():
#             continue
#         if mname == 'mysql.performance.kernel_time' and not Platform.is_linux():
#             continue
#         if mname == 'mysql.performance.cpu_time' and Platform.is_windows():
#             continue
#
#         if mname == 'mysql.performance.query_run_time.avg':
#             self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:testdb'], count=1)
#         elif mname == 'mysql.info.schema.size':
#             self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:testdb'], count=1)
#             self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:information_schema'], count=1)
#             self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:performance_schema'], count=1)
#         else:
#             self.assertMetric(mname, tags=self.METRIC_TAGS, at_least=0)
#
#     # Assert service metadata
#     self.assertServiceMetadata(['version'], count=1)
#
#     # test custom query metrics
#     self.assertMetric('alice.age', value=25)
#     self.assertMetric('bob.age', value=20)
#
#     # test optional metrics
#     self._test_optional_metrics((self.OPTIONAL_REPLICATION_METRICS +
#                                  self.OPTIONAL_INNODB_VARS +
#                                  self.OPTIONAL_STATUS_VARS +
#                                  self.OPTIONAL_STATUS_VARS_5_6_6), 1)
#
#     # Raises when coverage < 100%
#     self.coverage_report()
#
#


def _test_optional_metrics(aggregator, optional_metrics, at_least):
    """
    Check optional metrics - there should be at least `at_least` matches
    """

    before = len(aggregator.not_asserted())

    for mname in optional_metrics:
        aggregator.assert_metric(mname, tags=variables.METRIC_TAGS, at_least=0)

    # Compute match rate
    after = len(aggregator.not_asserted())

    self.assertTrue(after - before > at_least)
