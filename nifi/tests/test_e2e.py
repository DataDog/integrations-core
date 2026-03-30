# ABOUTME: End-to-end tests for the NiFi integration.
# ABOUTME: Runs the check via the Datadog Agent container against a real NiFi instance.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    aggregator.assert_metric('nifi.can_connect')
    aggregator.assert_metric('nifi.system.jvm.heap_used')
    aggregator.assert_metric('nifi.flow.running_count')
    aggregator.assert_metric('nifi.process_group.flowfiles_queued')
