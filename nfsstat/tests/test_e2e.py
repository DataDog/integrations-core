# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import CONFIG, CONFIG_BUNDLED_BINARY, METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_e2e_bundled_binary_no_mounts(dd_agent_check):
    """Verify the agent's bundled nfsiostat binary exists and the check handles no NFS mounts gracefully."""
    aggregator = dd_agent_check(CONFIG_BUNDLED_BINARY)

    aggregator.assert_all_metrics_covered()
