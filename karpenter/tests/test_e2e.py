# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics

from . import common


@pytest.mark.e2e
def test_check_karpenter_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    metrics = common.TEST_METRICS

    for metric in metrics:
        aggregator.assert_metric(name=metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('karpenter.openmetrics.health', ServiceCheck.OK, count=2)
