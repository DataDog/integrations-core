# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import AGENT_V2_METRICS, OPERATOR_V2_PROCESS_METRICS, OPTIONAL_METRICS, requires_new_environment

pytestmark = [requires_new_environment]


@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric in AGENT_V2_METRICS + OPERATOR_V2_PROCESS_METRICS:
        if metric in OPTIONAL_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric, at_least=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
