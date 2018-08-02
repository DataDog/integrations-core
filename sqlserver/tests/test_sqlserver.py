# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import conftest
from datadog_checks.sqlserver.sqlserver import SQLServer
"""
Runs against AppVeyor's SQLServer setups with their default configurations
"""

'''
def test_check_no_connection(aggregator, get_config):
    invalid_instance = {
        'host': '(local)\SQL2012SP1',
        'username': 'sa',
        'password': 'InvalidPassword',
        'timeout': 1,
        'tags': ['optional:tag1'],
    }
    get_config['instances'] = invalid_instance
    sqlserver_check = SQLServer(conftest.CHECK_NAME, get_config, {}, [invalid_instance])
    sqlserver_check.check(invalid_instance)

    with pytest.raises(Exception) as excinfo:
        sqlserver_check.check(invalid_instance)
    assert excinfo.value.args[0] == 'Unable to connect to SQL Server'
    aggregator.assert_service_checkl('sqlserver.can_connect', status=sqlserver_check.CRITICAL,
                                     tags=['host:(local)\SQL2012SP1', 'db:master', 'optional:tag1'])
'''


def test_check_2012(aggregator, get_sql2012_instance):
    sqlserver_check = SQLServer(conftest.CHECK_NAME, {}, {}, [get_sql2012_instance])
    sqlserver_check.check(get_sql2012_instance)

    # Make sure ALL custom metric is tagged by database
    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')
    custom_tags = get_sql2012_instance.get('tags', [])
    expected_tags = custom_tags + ['host:{}'.format(get_sql2012_instance.get('host')), 'db:master']
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

'''

'''
def test_check_linux(aggregator, spin_up_sqlserver, get_linux_instance):
    sqlserver_check = SQLServer(conftest.CHECK_NAME, {}, {}, [get_linux_instance])
    sqlserver_check.check(get_linux_instance)

    # Make sure ALL custom metric is tagged by database
    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')
    custom_tags = get_linux_instance.get('tags', [])
    expected_tags = custom_tags + ['host:{}'.format(get_linux_instance.get('host')), 'db:master']
    for mname in conftest.EXPECTED_METRICS:
        aggregator.assert_metric(mname, count=1)
    aggregator.assert_service_check('sqlserver.can_connect', status=sqlserver_check.OK, tags=expected_tags)
    aggregator.assert_all_metrics_covered
'''
