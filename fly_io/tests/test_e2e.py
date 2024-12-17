# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import USE_FLY_LAB
from .conftest import INSTANCE
from .metrics import ALL_PROMETHEUS_METRICS, ALL_REST_METRICS


@pytest.mark.e2e
@pytest.mark.skipif(USE_FLY_LAB, reason='Only run tests on one environment')
def test_e2e(dd_agent_check):
    instance = INSTANCE
    aggregator = dd_agent_check(instance, rate=True)

    aggregator.assert_service_check('fly_io.openmetrics.health', ServiceCheck.OK, count=2)
    for metric in ALL_PROMETHEUS_METRICS + ALL_REST_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
