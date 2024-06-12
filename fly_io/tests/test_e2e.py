# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import MOCKED_METRICS
from .conftest import INSTANCE


@pytest.mark.e2e
def test_e2e_openmetrics(dd_agent_check):
    instance = INSTANCE
    aggregator = dd_agent_check(instance, rate=True)

    aggregator.assert_service_check('fly_io.openmetrics.health', ServiceCheck.OK, count=2)
    for metric in MOCKED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
