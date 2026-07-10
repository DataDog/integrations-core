# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.marathon import Marathon

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery()

    # The `tags` and `label_tags` config fields aren't derivable from container
    # discovery, so metrics are asserted without `common.EXPECTED_TAGS` here.
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, Marathon, compose_service='marathon')
