# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.sqlserver import SQLConnectionError


CHECK_NAME = 'sqlserver'
EXPECTED_METRICS = [m[0] for m in SQLServer.METRICS]


@pytest.mark.docker
def test_check_invalid_password(aggregator, init_config, instance_docker, sqlserver):
    instance_docker['password'] = 'FOO'

    sqlserver_check = SQLServer(CHECK_NAME, init_config, {}, [instance_docker])

    with pytest.raises(SQLConnectionError) as excinfo:
        sqlserver_check.check(instance_docker)
        assert excinfo.value.args[0] == 'Unable to connect to SQL Server'
    aggregator.assert_service_check('sqlserver.can_connect', status=sqlserver_check.CRITICAL,
                                    tags=['host:localhost,1433', 'db:master', 'optional:tag1'])


@pytest.mark.docker
def test_check_docker(aggregator, init_config, instance_docker, sqlserver):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, {}, [instance_docker])
    sqlserver_check.check(instance_docker)
    expected_tags = instance_docker.get('tags', []) + ['host:{}'.format(instance_docker.get('host')), 'db:master']
    _assert_metrics(aggregator, expected_tags)


@pytest.mark.docker
def test_object_name(aggregator, instance_docker, sqlserver):
    init_config_object_name = {
        'custom_metrics': [
            {
                'name': 'sqlserver.cache.hit_ratio',
                'counter_name': 'Cache Hit Ratio',
                'instance_name': 'SQL Plans',
                'object_name': 'SQLServer:Plan Cache',
                'tags': [
                    'optional_tag:tag1'
                ]
            },
            {
                'name': 'sqlserver.active_requests',
                'counter_name': 'Active requests',
                'instance_name': 'default',
                'object_name': 'SQLServer:Workload Group Stats',
                'tags': [
                    'optional_tag:tag1'
                ]
            }
        ]
    }

    sqlserver_check = SQLServer(CHECK_NAME, init_config_object_name, {}, [instance_docker])
    sqlserver_check.check(instance_docker)

    aggregator.assert_metric('sqlserver.cache.hit_ratio', tags=['optional:tag1', 'optional_tag:tag1'], count=1)
    aggregator.assert_metric('sqlserver.active_requests', tags=['optional:tag1', 'optional_tag:tag1'], count=1)


@pytest.mark.local
def test_check_local(aggregator, init_config, instance_sql2008):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, {}, [instance_sql2008])
    sqlserver_check.check(instance_sql2008)
    expected_tags = instance_sql2008.get('tags', []) + ['host:(local)\SQL2008R2SP2', 'db:master']
    _assert_metrics(aggregator, expected_tags)


def _assert_metrics(aggregator, expected_tags):
    """
    Boilerplate asserting all the expected metrics and service checks.
    Make sure ALL custom metric is tagged by database.
    """
    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')
    for mname in EXPECTED_METRICS:
        aggregator.assert_metric(mname, count=1)
    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK, tags=expected_tags)
    aggregator.assert_all_metrics_covered
