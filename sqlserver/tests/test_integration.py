# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import copy, deepcopy

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.sqlserver import SQLConnectionError

from .common import CHECK_NAME, CUSTOM_QUERY_A, CUSTOM_QUERY_B, assert_metrics
from .utils import not_windows_ci

try:
    import pyodbc
except ImportError:
    pyodbc = None


pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment"), not_windows_ci]


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


def test_check_docker(aggregator, init_config, instance_docker):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    sqlserver_check.check(instance_docker)
    expected_tags = instance_docker.get('tags', []) + ['host:{}'.format(instance_docker.get('host')), 'db:master']
    assert_metrics(aggregator, expected_tags)


def load_stored_procedure(instance, proc_name, sp_tags):
    # Make DB connection
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
        instance['driver'], instance['host'], instance['username'], instance['password']
    )
    conn = pyodbc.connect(conn_str, timeout=30)

    # Create cursor associated with connection
    cursor = conn.cursor()

    # Stored Procedure Drop Statement
    sqlDropSP = "IF EXISTS (SELECT * FROM sys.objects \
               WHERE type='P' AND name='{0}') \
               DROP PROCEDURE {0}".format(
        proc_name
    )
    cursor.execute(sqlDropSP)

    # Stored Procedure Create Statement
    # Note: the INSERT statement uses single quotes (') intentionally
    # Double-quotes caused the odd error: "Invalid column name 'sql.sp.testa'."
    # https://dba.stackexchange.com/a/219875
    sqlCreateSP = """\
    CREATE PROCEDURE {0} AS
        BEGIN
            CREATE TABLE #Datadog
            (
              [metric] varchar(255) not null,
              [type] varchar(50) not null,
              [value] float not null,
              [tags] varchar(255)
            )
            SET NOCOUNT ON;
            INSERT INTO #Datadog (metric, type, value, tags) VALUES
                ('sql.sp.testa', 'gauge', 100, '{1}'),
                ('sql.sp.testb', 'gauge', 1, '{1}'),
                ('sql.sp.testb', 'gauge', 2, '{1}');
            SELECT * FROM #Datadog;
        END;
        """.format(
        proc_name, sp_tags
    )
    cursor.execute(sqlCreateSP)

    # # For debugging. Calls the stored procedure and prints the results.
    # # use call_proc for macOS
    # call_proc = '{{CALL {}}}'.format(proc)
    # cursor.execute(call_proc)
    # # otherwise just execute proc directly
    # # cursor.execute(proc)
    # rows = cursor.fetchall()
    # while rows:
    #     print(rows)
    #     if cursor.nextset():
    #         rows = cursor.fetchall()
    #     else:
    #         rows = None

    cursor.commit()
    cursor.close()


def test_check_stored_procedure(aggregator, init_config, instance_docker):
    instance_pass = deepcopy(instance_docker)

    proc = 'pyStoredProc'
    sp_tags = "foo:bar,baz:qux"
    instance_pass['stored_procedure'] = proc

    load_stored_procedure(instance_pass, proc, sp_tags)

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_pass])
    sqlserver_check.check(instance_docker)

    expected_tags = instance_pass.get('tags', []) + sp_tags.split(',')
    aggregator.assert_metric('sql.sp.testa', value=100, tags=expected_tags, count=1)
    aggregator.assert_metric('sql.sp.testb', tags=expected_tags, count=2)


def test_check_stored_procedure_proc_if(aggregator, init_config, instance_docker):
    instance_fail = deepcopy(instance_docker)
    proc = 'pyStoredProc'
    proc_only_fail = "select cntr_type from sys.dm_os_performance_counters where counter_name in ('FOO');"
    sp_tags = "foo:bar,baz:qux"

    instance_fail['proc_only_if'] = proc_only_fail
    instance_fail['stored_procedure'] = proc

    load_stored_procedure(instance_fail, proc, sp_tags)

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_fail])
    sqlserver_check.check(instance_fail)

    # apply a proc check that will never fail and assert that the metrics remain unchanged
    assert len(aggregator._metrics) == 0


def test_custom_metrics_object_name(aggregator, init_config_object_name, instance_docker):

    sqlserver_check = SQLServer(CHECK_NAME, init_config_object_name, [instance_docker])
    sqlserver_check.check(instance_docker)

    aggregator.assert_metric('sqlserver.cache.hit_ratio', tags=['optional:tag1', 'optional_tag:tag1'], count=1)
    aggregator.assert_metric('sqlserver.active_requests', tags=['optional:tag1', 'optional_tag:tag1'], count=1)


def test_custom_metrics_alt_tables(aggregator, init_config_alt_tables, instance_docker):
    instance = deepcopy(instance_docker)
    instance['include_task_scheduler_metrics'] = False

    sqlserver_check = SQLServer(CHECK_NAME, init_config_alt_tables, [instance])
    sqlserver_check.check(instance_docker)

    aggregator.assert_metric('sqlserver.LCK_M_S.max_wait_time_ms', tags=['optional:tag1'], count=1)
    aggregator.assert_metric('sqlserver.LCK_M_S.signal_wait_time_ms', tags=['optional:tag1'], count=1)
    aggregator.assert_metric(
        'sqlserver.MEMORYCLERK_BITMAP.virtual_memory_committed_kb', tags=['memory_node_id:0', 'optional:tag1'], count=1
    )
    aggregator.assert_metric(
        'sqlserver.MEMORYCLERK_BITMAP.virtual_memory_reserved_kb', tags=['memory_node_id:0', 'optional:tag1'], count=1
    )

    # check a second time for io metrics to be processed
    sqlserver_check.check(instance_docker)

    aggregator.assert_metric('sqlserver.io_file_stats.num_of_reads')
    aggregator.assert_metric('sqlserver.io_file_stats.num_of_writes')


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance_docker):
    instance = copy(instance_docker)
    querya = copy(CUSTOM_QUERY_A)
    queryb = copy(CUSTOM_QUERY_B)
    instance['custom_queries'] = [querya, queryb]

    check = SQLServer(CHECK_NAME, {}, [instance])
    check.check(instance)
    tags = list(instance['tags'])

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = ['customtag:{}'.format(tag)]
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags + ['query:custom'])
        aggregator.assert_metric('another_custom_one.num', value=value, tags=custom_tags + ['query:another_custom_one'])
