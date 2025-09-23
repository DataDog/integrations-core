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
    pg_instance['collect_schemas'] = {'enabled': True, 'run_sync': True}
    check = integration_check(pg_instance)
    inject_snapshot_observer(check, snapshot_mode)
    check.run()

    # Sanity check that the check ran
    aggregator.assert_metric("postgresql.running", count=1)

    validate_snapshot(aggregator, check)
