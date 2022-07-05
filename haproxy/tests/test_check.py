# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from .common import requires_new_environment

pytestmark = [requires_new_environment, pytest.mark.usefixtures('dd_environment')]


def test_check(aggregator, dd_run_check, instancev1, check, prometheus_metrics):
    dd_run_check(check(instancev1))

    for metric in prometheus_metrics:
        aggregator.assert_metric('haproxy.{}'.format(metric))

    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
def test_checkv2(aggregator, dd_run_check, check, instancev2, prometheus_metricsv2):
    dd_run_check(check(instancev2))

    for metric in prometheus_metricsv2:
        aggregator.assert_metric('haproxy.{}'.format(metric))

    aggregator.assert_all_metrics_covered()
