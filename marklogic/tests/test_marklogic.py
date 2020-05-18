# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.marklogic import MarklogicCheck

from .common import INSTANCE
from .metrics import GLOBAL_METRICS, STORAGE_HOST_METRICS, STORAGE_FOREST_METRICS


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = MarklogicCheck('marklogic', {}, [INSTANCE])

    check.check(INSTANCE)

    tags = ['foo:bar']

    for metric in GLOBAL_METRICS:
        aggregator.assert_metric(metric, tags=tags)

    storage_tag_prefixes = ['storage_path', 'host_name', 'host_id']
    for metric in STORAGE_HOST_METRICS:
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)
        for prefix in storage_tag_prefixes:
            aggregator.assert_metric_has_tag_prefix(metric, prefix)
    for metric in STORAGE_FOREST_METRICS:
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)
        for prefix in storage_tag_prefixes + ['forest_id', 'forest_name']:
            aggregator.assert_metric_has_tag_prefix(metric, prefix)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)

    for metric in GLOBAL_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()

