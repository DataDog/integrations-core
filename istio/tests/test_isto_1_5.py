# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.istio import Istio

from . import common


def test_istiod(aggregator, istiod_mixture_fixture):
    """
    Test the istiod deployment endpoint for v1.5+ check
    """
    check = Istio('istio', {}, [common.MOCK_ISTIOD_INSTANCE])
    check.check(common.MOCK_ISTIOD_INSTANCE)

    for metric in common.ISTIOD_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_istio_proxy_mesh(aggregator, istio_proxy_mesh_fixture):
    """
    Test proxy mesh check
    """
    check = Istio('istio', {}, [common.MOCK_ISTIO_PROXY_MESH_INSTANCE])
    check.check(common.MOCK_ISTIO_PROXY_MESH_INSTANCE)

    for metric in common.PROXY_MESH_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
