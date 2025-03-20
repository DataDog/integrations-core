# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import OPTIONAL_METRICS, TEST_METRICS


@pytest.mark.e2e
def test_check_velero_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for metric, _ in TEST_METRICS.items():
        if metric in OPTIONAL_METRICS:
            aggregator.assert_metric(name=metric, at_least=0)
        else:
            aggregator.assert_metric(name=metric, at_least=1)

    aggregator.assert_service_check('velero.openmetrics.health', ServiceCheck.OK)
