# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from datadog_checks.base import is_affirmative
from datadog_checks.dev.utils import get_metadata_metrics

from .common import ENDPOINT_PROMETHEUS, HAPROXY_LEGACY, requires_new_environment

pytestmark = [requires_new_environment, pytest.mark.e2e]


def test_check(dd_agent_check, instancev1, prometheus_metrics):
    aggregator = dd_agent_check(instancev1, rate=True)

    for metric in prometheus_metrics:
        aggregator.assert_metric('haproxy.{}'.format(metric))

    aggregator.assert_all_metrics_covered()

    exclude_metrics = []
    if not is_affirmative(HAPROXY_LEGACY):
        # These metrics are submitted as counts with Prometheus
        exclude_metrics = [
            'haproxy.backend.bytes.in.total',
            'haproxy.backend.bytes.out.total',
            'haproxy.frontend.bytes.in.total',
            'haproxy.frontend.bytes.out.total',
        ]
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=exclude_metrics)


@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
def test_checkv2(dd_agent_check, instancev2, prometheus_metricsv2):
    aggregator = dd_agent_check(instancev2, rate=True)

    for metric in prometheus_metricsv2:
        aggregator.assert_metric('haproxy.{}'.format(metric))
        aggregator.assert_metric_has_tag('haproxy.{}'.format(metric), tag="endpoint:" + ENDPOINT_PROMETHEUS)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
