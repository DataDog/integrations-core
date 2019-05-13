# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.kube_apiserver_metrics import KubeApiserverMetricsCheck


def test_check(aggregator, instance):
    check = KubeApiserverMetricsCheck('kube_apiserver_metrics', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
