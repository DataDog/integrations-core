# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import HEAD_INSTANCE, HEAD_METRICS, OPTIONAL_METRICS, WORKER1_INSTANCE, WORKER_METRICS

pytestmark = [pytest.mark.usefixtures("dd_environment")]


@pytest.mark.parametrize(
    'instance, metrics',
    [
        pytest.param(HEAD_INSTANCE, HEAD_METRICS, id='head'),
        pytest.param(WORKER1_INSTANCE, WORKER_METRICS, id='worker'),
    ],
)
def test_check(dd_run_check, aggregator, check, instance, metrics):
    dd_run_check(check(instance))

    for expected_metric in metrics:
        if expected_metric in OPTIONAL_METRICS:
            aggregator.assert_metric(expected_metric, at_least=0)
        else:
            aggregator.assert_metric(expected_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check("ray.openmetrics.health", status=AgentCheck.OK)
