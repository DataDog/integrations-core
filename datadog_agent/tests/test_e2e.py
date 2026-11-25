# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import pytest

from datadog_checks.dev.utils import get_metadata_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check: Any):
    aggregator = dd_agent_check(rate=True)

    # A standalone Agent without logs or DogStatsD traffic only exposes part of the default set, so assert the
    # metrics that are always present and that everything emitted is documented.
    for metric in ('datadog.agent.aggregator.number_of_flush.count', 'datadog.agent.scheduler.queues.size'):
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
