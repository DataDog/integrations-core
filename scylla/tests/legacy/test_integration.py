# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.scylla import ScyllaCheck
from tests.common import (
    FLAKY_METRICS,
    INSTANCE_DEFAULT_METRICS,
)


@pytest.mark.usefixtures('dd_environment')
def test_instance_integration_check(aggregator, mock_db_data, dd_run_check, instance_legacy):
    check = ScyllaCheck('scylla', {}, [instance_legacy])

    dd_run_check(check)
    dd_run_check(check)

    for m in INSTANCE_DEFAULT_METRICS:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, at_least=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', status=AgentCheck.OK)
