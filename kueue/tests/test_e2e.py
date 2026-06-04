# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metric('kueue.build_info')
    aggregator.assert_metric('kueue.go.goroutines')
    aggregator.assert_metric('kueue.cluster_queue.info', tags=['kueue_cluster_queue:cluster-queue'])
    aggregator.assert_metric('kueue.cluster_queue.status', tags=['kueue_cluster_queue:cluster-queue', 'status:active'])
    aggregator.assert_service_check('kueue.openmetrics.health', ServiceCheck.OK, count=1)
    assert_service_checks(aggregator)
