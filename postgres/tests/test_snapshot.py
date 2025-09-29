# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub

from .conftest import SnapshotMode
from .snapshots import (
    inject_snapshot_observer,
    validate_snapshot,
)


@pytest.mark.snapshot
def test_snapshot_dbm_false(aggregator: AggregatorStub, integration_check, pg_instance, snapshot_mode: SnapshotMode):
    check = integration_check(pg_instance)
    inject_snapshot_observer(check, snapshot_mode)
    check.run()

    # Sanity check that the check ran
    aggregator.assert_metric("postgresql.running", count=1)

    validate_snapshot(aggregator, check)


@pytest.mark.snapshot
def test_snapshot_dbm_true(aggregator: AggregatorStub, integration_check, pg_instance, snapshot_mode: SnapshotMode):
    pg_instance['dbm'] = True
    pg_instance['query_samples'] = {'enabled': True, 'run_sync': True}
    pg_instance['query_metrics'] = {'enabled': True, 'run_sync': True}
    pg_instance['query_activity'] = {'enabled': True, 'run_sync': True}
    pg_instance['collect_settings'] = {'enabled': True, 'run_sync': True}
    pg_instance['collect_schemas'] = {'enabled': False, 'run_sync': True}
    check = integration_check(pg_instance)
    inject_snapshot_observer(check, snapshot_mode)
    check.run()

    # Sanity check that the check ran
    aggregator.assert_metric("postgresql.running", count=1)

    validate_snapshot(aggregator, check)


@pytest.mark.snapshot
def test_snapshot_dbm_true_autodiscovery(
    aggregator: AggregatorStub, integration_check, pg_instance, snapshot_mode: SnapshotMode
):
    pg_instance['dbm'] = True
    pg_instance['query_samples'] = {'enabled': True, 'run_sync': True}
    pg_instance['query_metrics'] = {'enabled': True, 'run_sync': True}
    pg_instance['query_activity'] = {'enabled': True, 'run_sync': True}
    pg_instance['collect_settings'] = {'enabled': True, 'run_sync': True}
    pg_instance['collect_schemas'] = {'enabled': False, 'run_sync': True}
    pg_instance['database_autodiscovery'] = {'enabled': True, 'max_databases': 200}
    pg_instance['dbname'] = "postgres"
    check = integration_check(pg_instance)
    inject_snapshot_observer(check, snapshot_mode)
    check.run()

    # Sanity check that the check ran
    aggregator.assert_metric("postgresql.running", count=1)

    validate_snapshot(aggregator, check)


@pytest.mark.snapshot
def test_snapshot_custom_metrics(
    aggregator: AggregatorStub, integration_check, pg_instance, snapshot_mode: SnapshotMode
):
    pg_instance['dbm'] = False
    pg_instance['custom_metrics'] = [
        {
            "descriptors": [["datname", "db"]],
            "metrics": {"age(datfrozenxid) AS age": ["postgresql.xid_age", "GAUGE"]},
            "query": "SELECT datname, %s FROM pg_database WHERE datallowconn = TRUE;",
            "relation": False,
        },
        {
            "descriptors": [["slot_name", "replication_slot"]],
            "metrics": {
                "pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)": ["postgresql.replication_slot.lag", "GAUGE"]
            },
            "query": "SELECT slot_name, %s FROM pg_replication_slots;",
            "relation": False,
        },
    ]
    check = integration_check(pg_instance)
    inject_snapshot_observer(check, snapshot_mode)
    check.run()

    # Sanity check that the check ran
    aggregator.assert_metric("postgresql.running", count=1)
    validate_snapshot(aggregator, check)

@pytest.mark.snapshot
def test_snapshot_custom_queries(aggregator: AggregatorStub, integration_check, pg_instance, snapshot_mode: SnapshotMode):
    pg_instance['dbm'] = False
    pg_instance['custom_queries'] = [
        {
            'query': 'SELECT 1',
            'columns': [{'name': 'custom_metric', 'type': 'gauge'}],
        }
    ]
    check = integration_check(pg_instance)
    inject_snapshot_observer(check, snapshot_mode)
    check.run()

        # Sanity check that the check ran
    aggregator.assert_metric("postgresql.running", count=1)
    validate_snapshot(aggregator, check)
