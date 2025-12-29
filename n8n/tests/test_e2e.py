# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import assert_service_checks

def test_check_n8n_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    # Assert the readiness check metric is present with status_code tag
    aggregator.assert_metric('n8n.readiness.check', value=1, at_least=1)

    # Verify the metric has a status_code tag
    metrics = aggregator.metrics('n8n.readiness.check')
    assert len(metrics) > 0, "n8n.readiness.check metric not found"

    # Check that status_code tag is present
    tags = metrics[0].tags
    status_code_tags = [tag for tag in tags if tag.startswith('status_code:')]
    assert len(status_code_tags) == 1, f"Expected exactly one status_code tag, got {len(status_code_tags)}"
    assert status_code_tags[0] == 'status_code:200', f"Expected status_code:200, got {status_code_tags[0]}"

    assert_service_checks(aggregator)
