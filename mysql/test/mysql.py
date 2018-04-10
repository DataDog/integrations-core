# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from os import environ

# 3rd-party
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from utils.platform import Platform
from tests.checks.common import AgentCheckTest


@attr(requires='mysql')
class TestMySql(AgentCheckTest):

    def _test_optional_metrics(self, optional_metrics, at_least):
        """
        Check optional metrics - there should be at least `at_least` matches
        """

        before = len(filter(lambda m: m[3].get('tested'), self.metrics))

        for mname in optional_metrics:
            self.assertMetric(mname, tags=self.METRIC_TAGS, at_least=0)

        # Compute match rate
        after = len(filter(lambda m: m[3].get('tested'), self.metrics))

        self.assertTrue(after - before > at_least)

    def test_minimal_config(self):
        config = {'instances': self.MYSQL_MINIMAL_CONFIG}
        self.run_check_twice(config)

        # Test service check
        self.assertServiceCheck('mysql.can_connect', status=AgentCheck.OK,
                                tags=self.SC_TAGS_MIN, count=1)

        # Test metrics
        testable_metrics = (self.STATUS_VARS + self.VARIABLES_VARS + self.INNODB_VARS +
                            self.BINLOG_VARS + self.SYSTEM_METRICS + self.SYNTHETIC_VARS)

        for mname in testable_metrics:
            self.assertMetric(mname, at_least=0)

    def test_complex_config(self):
        config = {'instances': self.MYSQL_COMPLEX_CONFIG}
        self.run_check_twice(config)

        # Test service check
        self.assertServiceCheck('mysql.can_connect', status=AgentCheck.OK,
                                tags=self.SC_TAGS, count=1)

        self.assertServiceCheck('mysql.replication.slave_running', status=AgentCheck.OK,
                                tags=self.SC_TAGS, at_least=1)

        ver = map(lambda x: int(x), self.service_metadata[0]['version'].split("."))
        ver = tuple(ver)

        testable_metrics = (self.STATUS_VARS + self.VARIABLES_VARS + self.INNODB_VARS +
                            self.BINLOG_VARS + self.SYSTEM_METRICS + self.SCHEMA_VARS + self.SYNTHETIC_VARS)

        if ver >= (5, 6, 0) and environ.get('MYSQL_FLAVOR') != 'mariadb':
            testable_metrics.extend(self.PERFORMANCE_VARS)

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
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:testdb'], count=1)
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:mysql'], count=1)
            elif mname == 'mysql.info.schema.size':
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:testdb'], count=1)
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:information_schema'], count=1)
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:performance_schema'], count=1)
            else:
                self.assertMetric(mname, tags=self.METRIC_TAGS, at_least=0)

        # Assert service metadata
        self.assertServiceMetadata(['version'], count=1)

        # test custom query metrics
        self.assertMetric('alice.age', value=25)
        self.assertMetric('bob.age', value=20)

        # test optional metrics
        self._test_optional_metrics((self.OPTIONAL_REPLICATION_METRICS +
                                     self.OPTIONAL_INNODB_VARS +
                                     self.OPTIONAL_STATUS_VARS +
                                     self.OPTIONAL_STATUS_VARS_5_6_6), 1)

        # Raises when coverage < 100%
        self.coverage_report()

    def test_complex_config_replica(self):
        config = {'instances': self.MYSQL_COMPLEX_CONFIG}
        config['instances'][0]['port'] = 13307
        self.run_check_twice(config)

        self.assertMetricTag('mysql.replication.seconds_behind_master', 'channel:default')

        # Test service check
        self.assertServiceCheck('mysql.can_connect', status=AgentCheck.OK,
                                tags=self.SC_TAGS_REPLICA, count=1)

        # Travis MySQL not running replication - FIX in flavored test.
        self.assertServiceCheck('mysql.replication.slave_running', status=AgentCheck.OK,
                                tags=self.SC_TAGS_REPLICA, at_least=1)

        ver = map(lambda x: int(x), self.service_metadata[0]['version'].split("."))
        ver = tuple(ver)

        testable_metrics = (self.STATUS_VARS + self.VARIABLES_VARS + self.INNODB_VARS +
                            self.BINLOG_VARS + self.SYSTEM_METRICS + self.SCHEMA_VARS + self.SYNTHETIC_VARS)

        if ver >= (5, 6, 0) and environ.get('MYSQL_FLAVOR') != 'mariadb':
            testable_metrics.extend(self.PERFORMANCE_VARS)

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
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:testdb'], count=1)
            elif mname == 'mysql.info.schema.size':
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:testdb'], count=1)
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:information_schema'], count=1)
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:performance_schema'], count=1)
            else:
                self.assertMetric(mname, tags=self.METRIC_TAGS, at_least=0)

        # Assert service metadata
        self.assertServiceMetadata(['version'], count=1)

        # test custom query metrics
        self.assertMetric('alice.age', value=25)
        self.assertMetric('bob.age', value=20)

        # test optional metrics
        self._test_optional_metrics((self.OPTIONAL_REPLICATION_METRICS +
                                     self.OPTIONAL_INNODB_VARS +
                                     self.OPTIONAL_STATUS_VARS +
                                     self.OPTIONAL_STATUS_VARS_5_6_6), 1)

        # Raises when coverage < 100%
        self.coverage_report()

    def test_connection_failure(self):
        """
        Service check reports connection failure
        """
        config = {'instances': self.CONNECTION_FAILURE}

        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )

        self.assertServiceCheck('mysql.can_connect', status=AgentCheck.CRITICAL,
                                tags=self.SC_FAILURE_TAGS, count=1)
        self.coverage_report()
