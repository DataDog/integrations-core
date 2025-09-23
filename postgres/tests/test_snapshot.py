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
def test_snapshot(aggregator: AggregatorStub, integration_check, pg_instance, snapshot_mode: SnapshotMode):
    check = integration_check(pg_instance)
    inject_snapshot_observer(check, snapshot_mode)
    check.run()

    # Sanity check that the check ran
    aggregator.assert_metric("postgresql.running", count=1)

    validate_snapshot(aggregator, check)
