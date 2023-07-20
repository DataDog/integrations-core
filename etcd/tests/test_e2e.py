# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.etcd import Etcd

from .common import REMAPED_DEBUGGING_METRICS, URL
from .utils import is_leader

pytestmark = pytest.mark.e2e


def test_new(dd_agent_check, instance, openmetrics_metrics):
    aggregator = dd_agent_check(instance, rate=True)

    tags = ['is_leader:{}'.format('true' if is_leader(URL) else 'false')]

    for metric in openmetrics_metrics:
        aggregator.assert_metric('etcd.{}'.format(metric), tags=tags, at_least=0)

    for metric in REMAPED_DEBUGGING_METRICS:
        aggregator.assert_metric('etcd.{}'.format(metric), at_least=1)

    aggregator.assert_all_metrics_covered()

    service_check_tags = ['endpoint:{}'.format(instance['prometheus_url'])]

    aggregator.assert_service_check('etcd.prometheus.health', Etcd.OK, tags=service_check_tags, count=2)
