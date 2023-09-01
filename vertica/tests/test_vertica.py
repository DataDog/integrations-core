# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.vertica import VerticaCheck
from datadog_checks.vertica.vertica import VerticaClient

from . import common
from .metrics import ALL_METRICS


@pytest.mark.e2e
@pytest.mark.parametrize('connection_load_balance', [False, True])
def test_check_e2e(dd_agent_check, instance, connection_load_balance):
    instance["connection_load_balance"] = connection_load_balance
    aggregator = dd_agent_check(instance, rate=True)

    for metric in ALL_METRICS:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, datadog_agent, instance, dd_run_check):

    check = VerticaCheck('vertica', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    for metric in ALL_METRICS:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')

    aggregator.assert_all_metrics_covered()

    major_version = common.VERTICA_MAJOR_VERSION
    version_metadata = {'version.scheme': 'semver', 'version.major': str(major_version)}
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata) + 4)


@pytest.mark.usefixtures('dd_environment')
def test_vertica_log_file_not_created(aggregator, instance, dd_run_check):
    instance['client_lib_log_level'] = 'DEBUG'

    vertica_default_log = os.path.join(os.path.dirname(common.HERE), 'vertica_python.log')
    if os.path.exists(vertica_default_log):
        os.remove(vertica_default_log)

    check = VerticaCheck('vertica', {}, [instance])
    dd_run_check(check)
    assert not os.path.exists(vertica_default_log)


@pytest.mark.usefixtures('dd_environment')
def test_check_connection_load_balance(monkeypatch):
    options = common.connection_options_from_config(common.CONFIG)
    options['connection_load_balance'] = True
    client = VerticaClient(options)

    client.connect()
    old_connection = client.connection
    client.connect()

    assert client.connection != old_connection


@pytest.mark.usefixtures('dd_environment')
def test_connect_resets_connection_when_connection_closed():
    options = common.connection_options_from_config(common.CONFIG)
    client = VerticaClient(options)

    client.connect()
    client.connection.close()

    old_connection = client.connection
    client.connect()

    assert client.connection != old_connection


@pytest.mark.usefixtures('dd_environment')
def test_connect_when_connection_is_open_reuses_connection():
    options = common.connection_options_from_config(common.CONFIG)
    client = VerticaClient(options)

    conn = client.connect()
    assert client.connect() == conn


@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance, dd_run_check):
    instance['custom_queries'] = [
        {
            'tags': ['test:vertica'],
            'query': 'SELECT force_outer, table_name FROM v_catalog.tables',
            'columns': [{'name': 'table.force_outer', 'type': 'gauge'}, {'name': 'table_name', 'type': 'tag'}],
        }
    ]

    check = VerticaCheck('vertica', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'vertica.table.force_outer', metric_type=0, tags=['db:datadog', 'foo:bar', 'test:vertica', 'table_name:datadog']
    )


@pytest.mark.usefixtures('dd_environment')
def test_include_all_metric_groups(aggregator, instance, dd_run_check):
    check = VerticaCheck('vertica', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('vertica.license.expiration', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.license.size', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.node.total', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.projection.total', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.row.total', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.delete_vectors', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.memory.swap.total', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.query.active', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.resource_pool.memory.max', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.storage.size', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.node.resource_requests', metric_type=aggregator.GAUGE)


@pytest.mark.usefixtures('dd_environment')
def test_include_system_metric_group(aggregator, instance, dd_run_check):
    instance['metric_groups'] = ['system']

    check = VerticaCheck('vertica', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('vertica.node.total', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.node.down', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.node.allowed', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.node.available', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.ksafety.current', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.ksafety.intended', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.epoch.ahm', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.epoch.current', metric_type=aggregator.GAUGE)
    aggregator.assert_metric('vertica.epoch.last_good', metric_type=aggregator.GAUGE)

    aggregator.assert_all_metrics_covered()
