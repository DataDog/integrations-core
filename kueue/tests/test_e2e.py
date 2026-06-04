# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metric('kueue.build_info', at_least=1)
    aggregator.assert_metric('kueue.go.goroutines', at_least=1)
    aggregator.assert_metric('kueue.cluster_queue.info', at_least=1)
    aggregator.assert_metric('kueue.cluster_queue.status', at_least=1)

    for metric in ('kueue.cluster_queue.info', 'kueue.cluster_queue.status'):
        aggregator.assert_metric_has_tag(metric, 'kueue_cluster_queue:cluster-queue')

    aggregator.assert_service_check('kueue.openmetrics.health', ServiceCheck.OK, count=1)
    assert_service_checks(aggregator)
