# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from datadog_checks.dev.utils import get_metadata_metrics

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    # trigger a job but wait for it to be in a running state before running check
    assert common.setup_mapreduce()

    aggregator = dd_agent_check(instance, rate=True)
    for metric in common.ELAPSED_TIME_BUCKET_METRICS:
        aggregator.assert_metric(metric)
    common.assert_metrics_covered(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
