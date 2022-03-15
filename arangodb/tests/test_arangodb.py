# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Dict

import pytest
from datadog_checks.arangodb import ArangodbCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from .common import METRICS


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance, dd_run_check):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = ArangodbCheck('arangodb', {}, [instance])
    dd_run_check(check)
    dd_run_check(check)
    base_tags = ['endpoint:http://localhost:8529/_admin/metrics/v2']
    aggregator.assert_all_metrics_covered()
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    for metric in METRICS:
        aggregator.assert_metric(metric)
        for tag in base_tags:
            aggregator.assert_metric_has_tag(metric, tag)
