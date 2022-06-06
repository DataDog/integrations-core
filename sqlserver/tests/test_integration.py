# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from copy import copy, deepcopy

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.connection import SQLConnectionError

from .common import CHECK_NAME, CUSTOM_METRICS, EXPECTED_DEFAULT_METRICS, assert_metrics
from .utils import not_windows_ci, windows_ci

try:
    import pyodbc
except ImportError:
    pyodbc = None


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_invalid_password(aggregator, dd_run_check, init_config, instance_docker):
    instance_docker['password'] = 'FOO'

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])

    with pytest.raises(SQLConnectionError):
        sqlserver_check.initialize_connection()
        sqlserver_check.check(instance_docker)
    aggregator.assert_service_check(
        'sqlserver.can_connect',
        status=sqlserver_check.CRITICAL,
        tags=['sqlserver_host:localhost,1433', 'db:master', 'optional:tag1'],
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('database_autodiscovery', [True, False])
def test_check_docker(aggregator, dd_run_check, init_config, instance_docker, database_autodiscovery):
    instance_docker['database_autodiscovery'] = database_autodiscovery
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    dd_run_check(sqlserver_check)
    expected_tags = instance_docker.get('tags', []) + [
        'sqlserver_host:{}'.format(instance_docker.get('host')),
        'db:master',
    ]
    assert_metrics(
        aggregator,
        expected_tags,
        hostname=sqlserver_check.resolved_hostname,
        database_autodiscovery=database_autodiscovery,
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_stored_procedure(aggregator, dd_run_check, init_config, instance_docker):
    proc = 'pyStoredProc'
    sp_tags = "foo:bar,baz:qux"
    instance_docker['stored_procedure'] = proc

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    dd_run_check(sqlserver_check)

    expected_tags = instance_docker.get('tags', []) + sp_tags.split(',')
    aggregator.assert_metric('sql.sp.testa', value=100, tags=expected_tags, count=1)
    aggregator.assert_metric('sql.sp.testb', tags=expected_tags, count=2)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_stored_procedure_proc_if(aggregator, dd_run_check, init_config, instance_docker):
    proc = 'pyStoredProc'
    proc_only_fail = "select cntr_type from sys.dm_os_performance_counters where counter_name in ('FOO');"

    instance_docker['proc_only_if'] = proc_only_fail
    instance_docker['stored_procedure'] = proc

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    dd_run_check(sqlserver_check)

    # apply a proc check that will never fail and assert that the metrics remain unchanged
    assert len(aggregator._metrics) == 0


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_metrics_object_name(aggregator, dd_run_check, init_config_object_name, instance_docker):
    sqlserver_check = SQLServer(CHECK_NAME, init_config_object_name, [instance_docker])
    dd_run_check(sqlserver_check)

    aggregator.assert_metric('sqlserver.cache.hit_ratio', tags=['optional:tag1', 'optional_tag:tag1'], count=1)
    aggregator.assert_metric(
        'sqlserver.broker_activation.tasks_running', tags=['optional:tag1', 'optional_tag:tag1'], count=1
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_metrics_alt_tables(aggregator, dd_run_check, init_config_alt_tables, instance_docker):
    instance_docker['include_task_scheduler_metrics'] = False

    sqlserver_check = SQLServer(CHECK_NAME, init_config_alt_tables, [instance_docker])
    dd_run_check(sqlserver_check)

    aggregator.assert_metric('sqlserver.LCK_M_S.max_wait_time_ms', tags=['optional:tag1'], count=1)
    aggregator.assert_metric('sqlserver.LCK_M_S.signal_wait_time_ms', tags=['optional:tag1'], count=1)
    aggregator.assert_metric(
        'sqlserver.MEMORYCLERK_SQLGENERAL.virtual_memory_committed_kb',
        tags=['memory_node_id:0', 'optional:tag1'],
        count=1,
    )
    aggregator.assert_metric(
        'sqlserver.MEMORYCLERK_SQLGENERAL.virtual_memory_reserved_kb',
        tags=['memory_node_id:0', 'optional:tag1'],
        count=1,
    )

    # check a second time for io metrics to be processed
    dd_run_check(sqlserver_check)

    aggregator.assert_metric('sqlserver.io_file_stats.num_of_reads')
    aggregator.assert_metric('sqlserver.io_file_stats.num_of_writes')


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_database_metrics(aggregator, dd_run_check, instance_autodiscovery):
    instance_autodiscovery['autodiscovery_include'] = ['master', 'msdb']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    dd_run_check(check)

    master_tags = [
        'database:master',
        'database_files_state_desc:ONLINE',
        'file_id:1',
        'file_location:/var/opt/mssql/data/master.mdf',
        'file_type:data',
        'optional:tag1',
    ]
    msdb_tags = [
        'database:msdb',
        'database_files_state_desc:ONLINE',
        'file_id:1',
        'file_location:/var/opt/mssql/data/MSDBData.mdf',
        'file_type:data',
        'optional:tag1',
    ]
    aggregator.assert_metric('sqlserver.database.files.size', tags=master_tags)
    aggregator.assert_metric('sqlserver.database.files.size', tags=msdb_tags)
    aggregator.assert_metric('sqlserver.database.files.state', tags=master_tags)
    aggregator.assert_metric('sqlserver.database.files.state', tags=msdb_tags)


@pytest.mark.integration
@pytest.mark.parametrize(
    'service_check_enabled, default_count, extra_count',
    [(True, 4, 1), (False, 0, 0)],
)
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_db_service_checks(
    aggregator, dd_run_check, instance_autodiscovery, service_check_enabled, default_count, extra_count
):
    instance_autodiscovery['autodiscovery_include'] = ['master', 'msdb', 'unavailable_db']
    instance_autodiscovery['autodiscovery_db_service_check'] = service_check_enabled
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    dd_run_check(check)

    # verify that the old status check returns OK
    aggregator.assert_service_check(
        'sqlserver.can_connect',
        tags=['db:master', 'optional:tag1', 'sqlserver_host:localhost,1433'],
        status=SQLServer.OK,
    )

    # verify all databses in autodiscovery have a service check
    aggregator.assert_service_check(
        'sqlserver.database.can_connect',
        count=default_count,
        tags=['db:master', 'optional:tag1', 'sqlserver_host:localhost,1433'],
        status=SQLServer.OK,
    )
    aggregator.assert_service_check(
        'sqlserver.database.can_connect',
        count=extra_count,
        tags=['db:msdb', 'optional:tag1', 'sqlserver_host:localhost,1433'],
        status=SQLServer.OK,
    )
    # unavailable_db is an 'offline' database which prevents connections so we expect this service check to be
    # critical but not cause a failure of the check
    aggregator.assert_service_check(
        'sqlserver.database.can_connect',
        count=extra_count,
        tags=['db:unavailable_db', 'optional:tag1', 'sqlserver_host:localhost,1433'],
        status=SQLServer.CRITICAL,
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_exclude_db_service_checks(aggregator, dd_run_check, instance_autodiscovery):
    instance_autodiscovery['autodiscovery_include'] = ['master']
    instance_autodiscovery['autodiscovery_exclude'] = ['msdb']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])

    dd_run_check(check)

    # assert no connection is created for an excluded database
    aggregator.assert_service_check(
        'sqlserver.database.can_connect',
        tags=['db:msdb', 'optional:tag1', 'sqlserver_host:localhost,1433'],
        status=SQLServer.OK,
        count=0,
    )
    aggregator.assert_service_check(
        'sqlserver.database.can_connect',
        tags=['db:master', 'optional:tag1', 'sqlserver_host:localhost,1433'],
        status=SQLServer.OK,
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_no_autodiscovery_service_checks(aggregator, dd_run_check, init_config, instance_docker):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker])
    dd_run_check(sqlserver_check)

    # assert no database service checks
    aggregator.assert_service_check('sqlserver.database.can_connect', count=0)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_perf_counters(aggregator, dd_run_check, instance_autodiscovery):
    instance_autodiscovery['autodiscovery_include'] = ['master', 'msdb']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    dd_run_check(check)

    expected_metrics = [
        'sqlserver.database.backup_restore_throughput',
        'sqlserver.database.log_bytes_flushed',
        'sqlserver.database.log_flushes',
        'sqlserver.database.log_flush_wait',
        'sqlserver.database.transactions',
        'sqlserver.database.write_transactions',
        'sqlserver.database.active_transactions',
    ]
    master_tags = [
        'database:master',
        'optional:tag1',
    ]
    msdb_tags = [
        'database:msdb',
        'optional:tag1',
    ]
    base_tags = ['optional:tag1']
    for metric in expected_metrics:
        aggregator.assert_metric(metric, tags=master_tags)
        aggregator.assert_metric(metric, tags=msdb_tags)
        aggregator.assert_metric(metric, tags=base_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_perf_counters_doesnt_duplicate_names_of_metrics_to_collect(dd_run_check, instance_autodiscovery):
    instance_autodiscovery['autodiscovery_include'] = ['master', 'msdb']
    check = SQLServer(CHECK_NAME, {}, [instance_autodiscovery])
    dd_run_check(check)

    for _cls, metric_names in check.instance_per_type_metrics.items():
        expected = list(set(metric_names))
        assert sorted(metric_names) == sorted(expected)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_multiple_instances(aggregator, dd_run_check, instance_autodiscovery, caplog):
    caplog.clear()
    caplog.set_level(logging.DEBUG)

    instance_1 = deepcopy(instance_autodiscovery)
    instance_2 = deepcopy(instance_autodiscovery)

    instance_1['autodiscovery_include'] = ['model']
    instance_2['autodiscovery_include'] = ['msdb']

    check = SQLServer(CHECK_NAME, {}, instances=[instance_1, instance_2])
    dd_run_check(check)

    check = SQLServer(CHECK_NAME, {}, instances=[instance_2, instance_1])
    dd_run_check(check)

    found_log = 0
    for _, _, message in caplog.record_tuples:
        # make sure model is only queried once
        if "SqlDatabaseFileStats: changing cursor context via use statement: use [model]" in message:
            found_log += 1

    assert found_log == 1


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "custom_query, assert_metrics",
    [
        (
            {
                'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b')) AS t (num,letter)",
                'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
                'tags': ['query:custom'],
            },
            [
                ("sqlserver.num", {"value": 97, "tags": ["customtag:a", "query:custom"]}),
                ("sqlserver.num", {"value": 98, "tags": ["customtag:b", "query:custom"]}),
            ],
        ),
        (
            {
                'query': "EXEC exampleProcWithoutNocount",
                'columns': [{'name': 'value', 'type': 'gauge'}],
                'tags': ['hello:there'],
            },
            [
                ("sqlserver.value", {"value": 1, "tags": ["hello:there"]}),
            ],
        ),
    ],
)
def test_custom_queries(aggregator, dd_run_check, instance_docker, custom_query, assert_metrics):
    instance = copy(instance_docker)
    instance['custom_queries'] = [custom_query]

    check = SQLServer(CHECK_NAME, {}, [instance])
    dd_run_check(check)

    for metric_name, kwargs in assert_metrics:
        kwargs = copy(kwargs)
        kwargs['tags'] = instance['tags'] + kwargs.get('tags', [])
        aggregator.assert_metric(metric_name, **kwargs)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_load_static_information(aggregator, dd_run_check, instance_docker):
    instance = copy(instance_docker)
    check = SQLServer(CHECK_NAME, {}, [instance])
    dd_run_check(check)
    assert 'version' in check.static_info_cache, "missing version static information"
    assert check.static_info_cache['version'], "empty version in static information"


@windows_ci
@pytest.mark.integration
def test_check_windows_defaults(aggregator, dd_run_check, init_config, instance_docker_defaults):
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_defaults])
    dd_run_check(check)

    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')

    for mname in EXPECTED_DEFAULT_METRICS + CUSTOM_METRICS:
        aggregator.assert_metric(mname)

    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK)
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "instance_host,split_host,split_port",
    [
        ("localhost,1433,some-typo", "localhost", "1433"),
        ("localhost, 1433,some-typo", "localhost", "1433"),
        ("localhost,1433", "localhost", "1433"),
        ("localhost", "localhost", None),
    ],
)
def test_split_sqlserver_host(instance_docker, instance_host, split_host, split_port):
    sqlserver_check = SQLServer(CHECK_NAME, {}, [instance_docker])
    s_host, s_port = sqlserver_check.split_sqlserver_host_port(instance_host)
    assert (s_host, s_port) == (split_host, split_port)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "dbm_enabled, instance_host, reported_hostname, expected_hostname",
    [
        (False, 'localhost,1433,some-typo', '', 'stubbed.hostname'),
        (True, 'localhost,1433', '', 'stubbed.hostname'),
        (False, 'localhost', '', 'stubbed.hostname'),
        (False, '8.8.8.8', '', 'stubbed.hostname'),
        (True, 'localhost', 'forced_hostname', 'forced_hostname'),
        (True, 'datadoghq.com,1433', '', 'datadoghq.com'),
        (True, 'datadoghq.com', '', 'datadoghq.com'),
        (True, 'datadoghq.com', 'forced_hostname', 'forced_hostname'),
        (True, '8.8.8.8,1433', '', '8.8.8.8'),
        (False, '8.8.8.8', 'forced_hostname', 'forced_hostname'),
    ],
)
def test_resolved_hostname(instance_docker, dbm_enabled, instance_host, reported_hostname, expected_hostname):
    instance_docker['dbm'] = dbm_enabled
    instance_docker['host'] = instance_host
    instance_docker['reported_hostname'] = reported_hostname
    sqlserver_check = SQLServer(CHECK_NAME, {}, [instance_docker])
    assert sqlserver_check.resolved_hostname == expected_hostname


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('database_autodiscovery', [True, False])
def test_index_fragmentation_metrics(aggregator, dd_run_check, instance_docker, database_autodiscovery):
    instance_docker['database_autodiscovery'] = database_autodiscovery
    sqlserver_check = SQLServer(CHECK_NAME, {}, [instance_docker])
    dd_run_check(sqlserver_check)
    seen_databases = set()
    for m in aggregator.metrics("sqlserver.database.avg_fragmentation_in_percent"):
        tags_by_key = {k: v for k, v in [t.split(':') for t in m.tags]}
        seen_databases.add(tags_by_key['database_name'])
        assert tags_by_key['object_name'].lower() != 'none'

    assert 'master' in seen_databases
    if database_autodiscovery:
        assert 'datadog_test' in seen_databases
