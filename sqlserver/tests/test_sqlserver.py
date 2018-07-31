# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# import copy
import conftest
from datadog_checks.sqlserver.sqlserver import SQLServer
"""
Runs against AppVeyor's SQLServer setups with their default configurations
"""


def test_check_linux(aggregator, spin_up_sqlserver, get_config, get_linux_instance):
    get_config['instances'] = get_linux_instance
    sqlserver_check = SQLServer(conftest.CHECK_NAME, get_config, {}, [get_linux_instance])
    sqlserver_check.check(get_linux_instance)

    # Check custom metrics
    aggregator.assert_metric('sqlserver.clr.execution', count=1)
    aggregator.assert_metric('sqlserver.exec.in_progress', count=1)

    # Make sure ALL custom metric is tagged by database
    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')
    custom_tags = get_linux_instance.get('tags', [])
    expected_tags = custom_tags + ['host:{}'.format(get_linux_instance.get('host')), 'db:master']
    for mname in conftest.EXPECTED_METRICS:
        aggregator.assert_metric(mname, count=1)
    aggregator.assert_service_check('sqlserver.can_connect', status=sqlserver_check.OK, tags=expected_tags)
    aggregator.assert_all_metrics_covered


'''

    @attr('fixme')
    def test_check_2008(self):
        config = copy.deepcopy(CONFIG)
        config['instances'] = [SQL2008_INSTANCE]
        self._test_check(config)

    def test_check_2012(self):
        config = copy.deepcopy(CONFIG)
        config['instances'] = [SQL2012_INSTANCE]
        self._test_check(config)

    @attr('fixme')
    def test_check_2014(self):
        config = copy.deepcopy(CONFIG)
        config['instances'] = [SQL2014_INSTANCE]
        self._test_check(config)

    def test_check_no_connection(self):
        config = copy.deepcopy(CONFIG)
        config['instances'] = [{
            'host': '(local)\SQL2012SP1',
            'username': 'sa',
            'password': 'InvalidPassword',
            'timeout': 1,
            'tags': ['optional:tag1'],
        }]

        with self.assertRaisesRegexp(Exception, 'Unable to connect to SQL Server'):
            self.run_check(config, force_reload=True)

        self.assertServiceCheckCritical('sqlserver.can_connect',
                                        tags=['host:(local)\SQL2012SP1', 'db:master', 'optional:tag1'])

@attr('unix')
@attr('fixme')
@attr(requires='sqlserver')
class TestSqlserverLinux(AgentCheckTest):
    """Basic Test for sqlserver integration."""

    def test_check(self):
        config = copy.deepcopy(CONFIG)
        config['instances'] = [LINUX_INSTANCE]

        self.run_check_twice(config, force_reload=True)

        # FIXME: assert something, someday

'''
