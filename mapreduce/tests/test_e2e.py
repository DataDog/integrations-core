# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics, get_service_checks

from .common import ELAPSED_TIME_BUCKET_METRICS, assert_metrics_covered, setup_mapreduce


def test_e2e(dd_agent_check, instance):
    # trigger a job but wait for it to be in a running state before running check
    assert setup_mapreduce()

    aggregator = dd_agent_check(instance, rate=True)

    for metric in ELAPSED_TIME_BUCKET_METRICS:
        # at_least=0 because sometimes the job is already done, and we don't get the metrics
        # This is still useful to assert metadata though
        aggregator.assert_metric(metric, at_least=0)

    assert_metrics_covered(aggregator, at_least=0)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check('mapreduce.resource_manager.can_connect', status=AgentCheck.OK)

    # The stub is in the base check and I don't want to bump the min version for testing purposes
    if hasattr(aggregator, 'assert_service_checks'):
        aggregator.assert_service_checks(get_service_checks())
