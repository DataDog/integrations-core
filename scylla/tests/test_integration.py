# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from datadog_checks.base import AgentCheck
from datadog_checks.scylla import ScyllaCheck

from .common import (
    FLAKY_METRICS,
    INSTANCE_DEFAULT_METRICS_V2,
)


@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.usefixtures('dd_environment')
def test_instance_integration_check_omv2(aggregator, mock_db_data, dd_run_check, instance):
    check = ScyllaCheck('scylla', {}, [instance])

    dd_run_check(check)
    dd_run_check(check)

    for m in INSTANCE_DEFAULT_METRICS_V2:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, at_least=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.openmetrics.health', status=AgentCheck.OK)
