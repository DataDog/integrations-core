# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    ADDL_GC_OPERATOR_METRICS,
    ADDL_OPERATOR_METRICS,
    AGENT_V1_METRICS,
    AGENT_V1_METRICS_EXCLUDE_METADATA_CHECK,
    AGENT_V2_METRICS,
    OPERATOR_V2_METRICS,
    requires_new_environment,
)

pytestmark = [requires_new_environment, pytest.mark.unit]


@pytest.mark.parametrize('use_openmetrics', [True, False])
def test_agent_check(aggregator, agent_instance_use_openmetrics, mock_agent_data, dd_run_check, check, use_openmetrics):
    c = check(agent_instance_use_openmetrics(use_openmetrics))
    dd_run_check(c)
    for m in AGENT_V2_METRICS if use_openmetrics else AGENT_V1_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), exclude=None if use_openmetrics else AGENT_V1_METRICS_EXCLUDE_METADATA_CHECK
    )


def test_operator_check(aggregator, operator_instance_use_openmetrics, mock_operator_data, dd_run_check, check):
    c = check(operator_instance_use_openmetrics(True))

    dd_run_check(c)
    for m in OPERATOR_V2_METRICS + ADDL_OPERATOR_METRICS + ADDL_GC_OPERATOR_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
