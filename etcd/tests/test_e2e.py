# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.etcd import Etcd

from .common import REMAPED_DEBUGGING_METRICS, STORE_METRICS, URL
from .utils import is_leader, legacy, preview

pytestmark = pytest.mark.e2e


@preview
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


@legacy
def test_legacy(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    tags = ['url:{}'.format(URL), 'etcd_state:{}'.format('leader' if is_leader(URL) else 'follower')]

    for mname in STORE_METRICS:
        aggregator.assert_metric('etcd.store.{}'.format(mname), tags=tags, at_least=1)

    aggregator.assert_metric('etcd.self.send.appendrequest.count', tags=tags, at_least=1)
    aggregator.assert_metric('etcd.self.recv.appendrequest.count', tags=tags, at_least=1)

    service_check_tags = ['url:{}'.format(URL), 'etcd_state:{}'.format('leader' if is_leader(URL) else 'follower')]

    aggregator.assert_service_check(Etcd.SERVICE_CHECK_NAME, tags=service_check_tags, count=2)
    aggregator.assert_service_check(Etcd.HEALTH_SERVICE_CHECK_NAME, tags=service_check_tags[:1], count=2)
