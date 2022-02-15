# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import EXPECTED_METRICS, METRICS_URL, OPTIONAL_METRICS

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def test_check(aggregator, dd_run_check, pulsar_check, instance):
    check = pulsar_check(instance)
    dd_run_check(check)

    aggregator.assert_service_check('pulsar.openmetrics.health', ServiceCheck.OK)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, f'endpoint:{METRICS_URL}')

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
