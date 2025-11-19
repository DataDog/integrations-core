# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import METRICS


@pytest.mark.e2e
def test_check_celery_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for metric in METRICS:
        aggregator.assert_metric(name=metric, at_least=1)

    aggregator.assert_service_check('celery.flower.openmetrics.health', ServiceCheck.OK)
