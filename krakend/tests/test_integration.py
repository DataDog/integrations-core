# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.krakend import KrakendCheck
from tests.helpers import get_metrics_from_metadata

pytestmark = [pytest.mark.usefixtures("dd_environment"), pytest.mark.integration]


@pytest.fixture
def ready_check(check: KrakendCheck, dd_run_check: Callable, aggregator: AggregatorStub):
    # Run check twice to get target_info metrics
    dd_run_check(check)
    dd_run_check(check)


@pytest.mark.usefixtures("ready_check")
def test_all_metadata_metrics_found(aggregator: AggregatorStub):
    """Test that the check can collect metrics from the running KrakenD instance."""
    metadata_metrics = get_metrics_from_metadata()
    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )
