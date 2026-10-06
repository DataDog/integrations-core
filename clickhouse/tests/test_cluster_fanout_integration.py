# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from time import time

import mock
import pytest
from clickhouse_connect import get_client as get_clickhouse_client

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.utils import (
    CLUSTER_NODE_TAG,
    CLUSTER_TAG,
    HOSTING_TYPE_TAG,
    REMOTE_GRANT,
    DbmCollectionStatus,
)

from .common import CLICKHOUSE_VERSION, is_legacy

# Defined alongside the `cluster` macro and `remote_servers` block in
# tests/docker/volumes/clickhouse.xml: a self-hosted style cluster deliberately not named
# 'default', so these tests fail if the fan-out logic ever goes back to assuming that name
# (see PR #24920).
TEST_CLUSTER_NAME = 'dd_test_cluster'

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures('dd_environment'),
    pytest.mark.skipif(
        is_legacy(CLICKHOUSE_VERSION),
        reason='dd_test_cluster is only defined in the non-legacy docker compose config',
    ),
]


def test_fanout_cluster_name_resolves_the_real_cluster(instance, dd_run_check):
    """A self-hosted deployment with a real cluster must fan out over it, not a hardcoded 'default'."""
    instance = {**instance, 'single_endpoint_mode': True}
    check = ClickhouseCheck('clickhouse', {}, [instance])
    dd_run_check(check)

    assert check.cluster_name == TEST_CLUSTER_NAME
    assert check.fanout_cluster_name == TEST_CLUSTER_NAME


def test_get_system_table_fans_out_over_the_resolved_cluster(instance, dd_run_check):
    instance = {**instance, 'single_endpoint_mode': True}
    check = ClickhouseCheck('clickhouse', {}, [instance])
    dd_run_check(check)

    table_ref = check.get_system_table('one')
    assert table_ref == f"clusterAllReplicas('{TEST_CLUSTER_NAME}', system.one)"

    # Executed for real: a hardcoded 'default' would either raise UNKNOWN_CLUSTER (no such
    # cluster on a self-hosted deployment) or silently read the stock local-only cluster instead.
    rows = check.execute_query_raw(f'SELECT count() FROM {table_ref}')
    assert rows[0][0] == 1


def test_database_instance_payload_carries_real_cluster_topology(aggregator, instance, dd_run_check):
    """The metadata payload reports topology read from the actual ClickHouse cluster."""
    instance = {**instance, 'single_endpoint_mode': True}
    check = ClickhouseCheck('clickhouse', {}, [instance])
    dd_run_check(check)

    connect_node = check.execute_query_raw('SELECT hostName()')[0][0]
    node_rows = check.execute_query_raw(
        f"SELECT hostName() FROM clusterAllReplicas('{TEST_CLUSTER_NAME}', system.one) "
        "SETTINGS skip_unavailable_shards=1"
    )
    nodes = sorted({row[0] for row in node_rows})
    events = aggregator.get_event_platform_events('dbm-metadata')
    event = next(event for event in events if event['kind'] == 'database_instance')

    assert event['metadata']['cluster_name'] == TEST_CLUSTER_NAME
    assert event['metadata']['connect_node'] == connect_node
    assert event['metadata']['nodes'] == nodes
    assert event['metadata']['single_endpoint_mode'] is True
    assert event['metadata']['hosting_type'] == check.hosting_type
    assert connect_node in nodes
    assert f'{CLUSTER_TAG}:{TEST_CLUSTER_NAME}' in event['tags']
    assert f'{HOSTING_TYPE_TAG}:{check.hosting_type}' in event['tags']


def test_single_endpoint_mode_metrics_carry_the_cluster_node_tag(aggregator, instance, dd_run_check):
    """The QueryManager queries built by get_queries() must actually execute against the resolved cluster."""
    instance = {**instance, 'single_endpoint_mode': True}
    check = ClickhouseCheck('clickhouse', {}, [instance])
    dd_run_check(check)

    node_tagged_metrics = [
        name
        for name in aggregator.metric_names
        for stub in aggregator.metrics(name)
        if any(tag.startswith(f'{CLUSTER_NODE_TAG}:') for tag in stub.tags)
    ]
    assert node_tagged_metrics, 'Expected at least one metric fanned out via clusterAllReplicas to carry a node tag'


RESTRICTED_USER = 'datadog_no_remote'
RESTRICTED_PASSWORD = 'Datadog123!'


@pytest.fixture
def restricted_instance(instance):
    """An Agent user that can read every system table but lacks the REMOTE grant the node fan-out needs."""
    admin = get_clickhouse_client(
        host=instance['server'], port=instance['port'], username=instance['username'], password=instance['password']
    )
    admin.command(f'DROP USER IF EXISTS {RESTRICTED_USER}')
    admin.command(f"CREATE USER {RESTRICTED_USER} IDENTIFIED WITH sha256_password BY '{RESTRICTED_PASSWORD}'")
    admin.command(f'GRANT SELECT ON system.* TO {RESTRICTED_USER}')
    admin.command(f'GRANT SELECT ON default.* TO {RESTRICTED_USER}')
    yield admin, {**instance, 'username': RESTRICTED_USER, 'password': RESTRICTED_PASSWORD}
    admin.command(f'DROP USER IF EXISTS {RESTRICTED_USER}')


def latest_dbm_collection(aggregator):
    events = aggregator.get_event_platform_events('dbm-metadata')
    return [event for event in events if event['kind'] == 'database_instance'][-1]['metadata']['dbm_collection']


def test_dbm_pauses_until_the_missing_grant_is_added(aggregator, restricted_instance, dd_run_check):
    admin, instance = restricted_instance
    check = ClickhouseCheck('clickhouse', {}, [{**instance, 'dbm': True, 'single_endpoint_mode': True}])
    with mock.patch.object(ClickhouseCheck, 'run_async_jobs') as run_async_jobs:
        dd_run_check(check)

        dbm_collection = latest_dbm_collection(aggregator)
        assert dbm_collection['status'] == DbmCollectionStatus.BLOCKED
        assert REMOTE_GRANT in dbm_collection['missing_grants']
        run_async_jobs.assert_not_called()
        aggregator.assert_service_check('clickhouse.can_connect', ClickhouseCheck.OK)

        admin.command(f'GRANT CREATE TEMPORARY TABLE, REMOTE ON *.* TO {RESTRICTED_USER}')
        with mock.patch('datadog_checks.clickhouse.clickhouse.time', return_value=time() + 301):
            dd_run_check(check)

        assert latest_dbm_collection(aggregator)['status'] == DbmCollectionStatus.ACTIVE
        run_async_jobs.assert_called_once()
