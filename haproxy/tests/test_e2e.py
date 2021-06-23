# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import is_affirmative
from datadog_checks.dev.utils import get_metadata_metrics

from . import common

pytestmark = [common.requires_new_environment, pytest.mark.e2e]


def test_check(dd_agent_check, prometheus_metrics):
    aggregator = dd_agent_check(common.INSTANCE, rate=True)

    for metric in prometheus_metrics:
        aggregator.assert_metric('haproxy.{}'.format(metric))

    aggregator.assert_all_metrics_covered()

    exclude_metrics = []
    if not is_affirmative(common.HAPROXY_LEGACY):
        # These metrics are submitted as counts with Prometheus
        exclude_metrics = [
            'haproxy.backend.bytes.in.total',
            'haproxy.backend.bytes.out.total',
            'haproxy.frontend.bytes.in.total',
            'haproxy.frontend.bytes.out.total',
        ]
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=exclude_metrics)
