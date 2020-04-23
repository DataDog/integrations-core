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
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_ISTIO_PROXY_MESH_INSTANCE])
    check.check(common.MOCK_ISTIO_PROXY_MESH_INSTANCE)

    for metric in common.MESH_METRICS + common.MESH_MERICS_1_5:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_istio_proxy_mesh_exclude(aggregator, istio_proxy_mesh_fixture):
    """
    Test proxy mesh check
    """
    exclude_tags = ['destination_app', 'destination_principal']
    instance = common.MOCK_ISTIO_PROXY_MESH_INSTANCE
    instance['exclude_labels'] = exclude_tags

    check = Istio(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    for metric in common.MESH_METRICS + common.MESH_MERICS_1_5:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_version_metadata(datadog_agent, istiod_mixture_fixture):
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_ISTIOD_INSTANCE])
    check.check_id = 'test:123'
    check.check(common.MOCK_ISTIOD_INSTANCE)

    # Use version mocked from istiod 1.5 fixture
    MOCK_VERSION = '1.5.0'

    major, minor, patch = MOCK_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': MOCK_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
