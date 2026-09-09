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
    OPERATOR_V2_PROCESS_METRICS,
    OPTIONAL_METRICS,
    requires_new_environment,
)

pytestmark = [requires_new_environment, pytest.mark.unit]


@pytest.mark.parametrize("use_openmetrics", [True, False])
def test_agent_check(aggregator, agent_instance_use_openmetrics, mock_agent_data, dd_run_check, check, use_openmetrics):
    c = check(agent_instance_use_openmetrics(use_openmetrics))
    dd_run_check(c)
    for m in AGENT_V2_METRICS if use_openmetrics else AGENT_V1_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        exclude=None if use_openmetrics else AGENT_V1_METRICS_EXCLUDE_METADATA_CHECK,
    )


def test_operator_check(aggregator, operator_instance_use_openmetrics, mock_operator_data, dd_run_check, check):
    c = check(operator_instance_use_openmetrics(True))

    dd_run_check(c)
    for m in OPERATOR_V2_METRICS + ADDL_OPERATOR_METRICS + ADDL_GC_OPERATOR_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_optional_metrics_are_asserted():
    # The E2E gate (test_e2e.py) only relaxes a metric to `at_least=0` when it appears in
    # OPTIONAL_METRICS. A stale or misspelled OPTIONAL_METRICS entry (e.g. after a metric rename)
    # would silently never match, so guard that every optional metric is one the E2E test asserts.
    asserted = set(AGENT_V2_METRICS) | set(OPERATOR_V2_PROCESS_METRICS)
    orphaned = OPTIONAL_METRICS - asserted
    assert not orphaned, f"OPTIONAL_METRICS entries not covered by an asserted metric: {sorted(orphaned)}"
