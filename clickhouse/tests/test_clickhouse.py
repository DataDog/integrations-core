# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CLICKHOUSE_VERSION
from .metrics import OPTIONAL_METRICS, get_metrics

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_check(aggregator, instance, dd_run_check):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    dd_run_check(check)
    server_tag = 'server:{}'.format(instance['server'])
    port_tag = 'port:{}'.format(instance['port'])
    metrics = get_metrics(CLICKHOUSE_VERSION)

    for metric in metrics:
        aggregator.assert_metric_has_tag(metric, port_tag, at_least=1)
        aggregator.assert_metric_has_tag(metric, server_tag, at_least=1)
        aggregator.assert_metric_has_tag(metric, 'db:default', at_least=1)
        aggregator.assert_metric_has_tag(metric, 'foo:bar', at_least=1)

    aggregator.assert_metric(
        'clickhouse.dictionary.item.current',
        tags=[server_tag, port_tag, 'db:default', 'foo:bar', 'dictionary:test'],
        at_least=1,
    )

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_service_check("clickhouse.can_connect", count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_custom_queries(aggregator, instance, dd_run_check):
    instance['custom_queries'] = [
        {
            'tags': ['test:clickhouse'],
            'query': 'SELECT COUNT(*) FROM system.settings WHERE changed',
            'columns': [{'name': 'settings.changed', 'type': 'gauge'}],
        }
    ]

    check = ClickhouseCheck('clickhouse', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'clickhouse.settings.changed',
        metric_type=0,
        tags=[
            'server:{}'.format(instance['server']),
            'port:{}'.format(instance['port']),
            'db:default',
            'foo:bar',
            'test:clickhouse',
        ],
    )


@pytest.mark.skipif(CLICKHOUSE_VERSION == 'latest', reason='Version `latest` is ever-changing, skipping')
def test_version_metadata(instance, datadog_agent, dd_run_check):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    datadog_agent.assert_metadata(
        'test:123', {'version.scheme': 'calver', 'version.year': CLICKHOUSE_VERSION.split(".")[0]}
    )


def test_database_instance_metadata(aggregator, instance, datadog_agent, dd_run_check):
    """Test that database_instance metadata is sent correctly."""
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.check_id = 'test:456'
    dd_run_check(check)

    # Get database monitoring metadata events
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

    # Find the database_instance event
    event = next((e for e in dbm_metadata if e['kind'] == 'database_instance'), None)

    assert event is not None, "database_instance metadata event should be sent"
    assert event['dbms'] == 'clickhouse'
    assert event['kind'] == 'database_instance'
    assert event['database_instance'] == check.database_identifier
    assert event['collection_interval'] == 300
    assert 'metadata' in event
    assert 'dbm' in event['metadata']
    assert 'connection_host' in event['metadata']
    assert event['metadata']['connection_host'] == instance['server']


def test_database_instance_metadata_with_cloud_metadata(aggregator, instance, datadog_agent, dd_run_check):
    """Test that database_instance metadata includes cloud metadata when configured."""
    instance = instance.copy()
    instance['aws'] = {'instance_endpoint': 'my-clickhouse.us-east-1.rds.amazonaws.com'}
    instance['gcp'] = {'project_id': 'my-project', 'instance_id': 'my-instance'}

    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.check_id = 'test:789'
    dd_run_check(check)

    # Get database monitoring metadata events
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

    # Find the database_instance event
    event = next((e for e in dbm_metadata if e['kind'] == 'database_instance'), None)

    assert event is not None
    assert 'cloud_metadata' in event
    assert 'aws' in event['cloud_metadata']
    assert event['cloud_metadata']['aws']['instance_endpoint'] == 'my-clickhouse.us-east-1.rds.amazonaws.com'
    assert 'gcp' in event['cloud_metadata']
    assert event['cloud_metadata']['gcp']['project_id'] == 'my-project'
    assert event['cloud_metadata']['gcp']['instance_id'] == 'my-instance'
