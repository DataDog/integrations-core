# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.utils import CLUSTER_NODE_TAG

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
