# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.sqlserver import SQLConnectionError

from .common import CHECK_NAME, EXPECTED_METRICS, LOCAL_SERVER
from .utils import not_windows_ci, windows_ci

try:
    import pyodbc
except ImportError:
    pyodbc = None


@not_windows_ci
@pytest.mark.usefixtures("dd_environment")
def test_check_invalid_password(aggregator, init_config, instance_docker):
    instance_docker['password'] = 'FOO'

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])

    with pytest.raises(SQLConnectionError) as excinfo:
        sqlserver_check.check(instance_docker)
        assert excinfo.value.args[0] == 'Unable to connect to SQL Server'
    aggregator.assert_service_check(
        'sqlserver.can_connect',
        status=sqlserver_check.CRITICAL,
        tags=['host:localhost,1433', 'db:master', 'optional:tag1'],
    )


@not_windows_ci
@pytest.mark.usefixtures("dd_environment")
def test_check_docker(aggregator, init_config, instance_docker):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    sqlserver_check.check(instance_docker)
    expected_tags = instance_docker.get('tags', []) + ['host:{}'.format(instance_docker.get('host')), 'db:master']
    _assert_metrics(aggregator, expected_tags)


@not_windows_ci
@pytest.mark.usefixtures("dd_environment")
def test_check_stored_procedure(aggregator, init_config, instance_docker):
    proc = 'pyStoredProc'
    sp_tags = "foo:bar,baz:qux"

    instance_docker['stored_procedure'] = proc
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])

    # Make DB connection
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
        instance_docker['driver'], instance_docker['host'], instance_docker['username'], instance_docker['password']
    )
    conn = pyodbc.connect(conn_str, timeout=30)

    # Create cursor associated with connection
    cursor = conn.cursor()

    # Stored Procedure Drop Statement
    sqlDropSP = "IF EXISTS (SELECT * FROM sys.objects \
               WHERE type='P' AND name='{0}') \
               DROP PROCEDURE {0}".format(
        proc
    )
    cursor.execute(sqlDropSP)

    # Stored Procedure Create Statement
    sqlCreateSP = 'CREATE PROCEDURE {0} AS \
                BEGIN \
                    CREATE TABLE #Datadog \
                    ( \
                      [metric] varchar(255) not null, \
                      [type] varchar(50) not null, \
                      [value] float not null, \
                      [tags] varchar(255) \
                    ) \
                    SET NOCOUNT ON; \
                    INSERT INTO #Datadog (metric, type, value, tags) VALUES \
                        ("sql.sp.testa", "gauge", 100, "{1}"), \
                        ("sql.sp.testb", "gauge", 1, "{1}"), \
                        ("sql.sp.testb", "gauge", 2, "{1}"); \
                    SELECT * FROM #Datadog; \
                END;'.format(
        proc, sp_tags
    )
    cursor.execute(sqlCreateSP)

    # For debugging. Calls the stored procedure and prints the results.
    # cursor.execute(proc)
    # rows = cursor.fetchall()
    # while rows:
    #     print(rows)
    #     if cursor.nextset():
    #         rows = cursor.fetchall()
    #     else:
    #         rows = None

    cursor.commit()
    cursor.close()

    sqlserver_check.check(instance_docker)

    expected_tags = instance_docker.get('tags', []) + sp_tags.split(',')
    aggregator.assert_metric('sql.sp.testa', value=100, tags=expected_tags, count=1)
    aggregator.assert_metric('sql.sp.testb', tags=expected_tags, count=2)


@not_windows_ci
@pytest.mark.usefixtures("dd_environment")
def test_object_name(aggregator, init_config_object_name, instance_docker):

    sqlserver_check = SQLServer(CHECK_NAME, init_config_object_name, [instance_docker])
    sqlserver_check.check(instance_docker)

    aggregator.assert_metric('sqlserver.cache.hit_ratio', tags=['optional:tag1', 'optional_tag:tag1'], count=1)
    aggregator.assert_metric('sqlserver.active_requests', tags=['optional:tag1', 'optional_tag:tag1'], count=1)


@windows_ci
def test_check_local(aggregator, init_config, instance_sql2017):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_sql2017])
    sqlserver_check.check(instance_sql2017)
    expected_tags = instance_sql2017.get('tags', []) + ['host:{}'.format(LOCAL_SERVER), 'db:master']
    _assert_metrics(aggregator, expected_tags)


@windows_ci
@pytest.mark.parametrize('adoprovider', ['SQLOLEDB', 'SQLNCLI11'])
def test_check_adoprovider(aggregator, init_config, instance_sql2017, adoprovider):
    instance = deepcopy(instance_sql2017)
    instance['adoprovider'] = adoprovider

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance])
    sqlserver_check.check(instance)
    expected_tags = instance.get('tags', []) + ['host:{}'.format(LOCAL_SERVER), 'db:master']
    _assert_metrics(aggregator, expected_tags)


@pytest.mark.e2e
def test_check_docker_e2e(dd_agent_check, init_config, instance_e2e):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_e2e]}, rate=True)

    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')

    for mname in EXPECTED_METRICS:
        aggregator.assert_metric(mname)

    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK)

    aggregator.assert_all_metrics_covered()


def _assert_metrics(aggregator, expected_tags):
    """
    Boilerplate asserting all the expected metrics and service checks.
    Make sure ALL custom metric is tagged by database.
    """
    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')
    for mname in EXPECTED_METRICS:
        aggregator.assert_metric(mname, count=1)
    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK, tags=expected_tags)
    aggregator.assert_all_metrics_covered()
