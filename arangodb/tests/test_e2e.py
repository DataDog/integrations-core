# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import METRICS, OPTIONAL_METRICS
from tenacity import retry, wait_fixed, stop_after_attempt


@pytest.mark.e2e
@retry(wait=wait_fixed(2), stop=stop_after_attempt(2))
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    base_tags = ['endpoint:http://localhost:8529/_admin/metrics/v2', 'server_mode:default']
    for metric in METRICS:
        if metric in OPTIONAL_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric, at_least=1)
        for tag in base_tags:
            aggregator.assert_metric_has_tag(metric, tag)
