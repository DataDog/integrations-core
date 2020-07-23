# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.external_dns import ExternalDNSCheck
from datadog_checks.external_dns.metrics import DEFAULT_METRICS

from .common import CHECK_NAME


@pytest.mark.usefixtures('mock_external_dns')
def test_external_dns(aggregator, instance):
    """
    Testing external_dns
    """

    c = ExternalDNSCheck('external_dns', {}, [instance])
    c.check(instance)

    for metric in DEFAULT_METRICS.values():
        metric = '{}.{}'.format(CHECK_NAME, metric)
        for tag in instance['tags']:
            aggregator.assert_metric_has_tag(metric, tag)

    aggregator.assert_all_metrics_covered()
