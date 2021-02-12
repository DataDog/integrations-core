# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck

from . import common


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check = check(instance)
    check.check(instance)
    assert_check(aggregator)


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    assert_check(aggregator)


def assert_check(aggregator):
    aggregator.assert_service_check('yarn.can_connect', AgentCheck.OK)
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric_has_tag(metric, common.YARN_CLUSTER_TAG)
        aggregator.assert_metric_has_tag(metric, common.LEGACY_CLUSTER_TAG)

    aggregator.assert_all_metrics_covered()
