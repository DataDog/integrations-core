# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import requests_mock

from datadog_checks.istio import Istio

from . import common
from .utils import _assert_tags_excluded, get_response


def test_legacy_istiod(aggregator):
    """
    Test the istiod deployment endpoint for v1.5+ check
    """
    check = Istio('istio', {}, [common.MOCK_LEGACY_ISTIOD_INSTANCE])
    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://localhost:8080/metrics', text=get_response('1.5', 'istiod.txt'))
        check.check(common.MOCK_LEGACY_ISTIOD_INSTANCE)

    for metric in common.ISTIOD_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_legacy_proxy_mesh(aggregator):
    """
    Test proxy mesh check
    """
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_LEGACY_MESH_INSTANCE])

    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://localhost:15090/metrics', text=get_response('1.5', 'istio-proxy.txt'))
        check.check(common.MOCK_LEGACY_MESH_INSTANCE)

    for metric in common.LEGACY_MESH_METRICS + common.MESH_MERICS_1_5:
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, [])

    aggregator.assert_all_metrics_covered()


def test_istio_proxy_mesh_exclude(aggregator):
    """
    Test proxy mesh check
    """
    exclude_tags = ['destination_app', 'destination_principal']
    instance = common.MOCK_LEGACY_MESH_INSTANCE
    instance['exclude_labels'] = exclude_tags

    check = Istio(common.CHECK_NAME, {}, [instance])

    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://localhost:15090/metrics', text=get_response('1.5', 'istio-proxy.txt'))
        check.check(instance)

    for metric in common.LEGACY_MESH_METRICS + common.MESH_MERICS_1_5:
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, exclude_tags)

    aggregator.assert_all_metrics_covered()


def test_legacy_version_metadata(datadog_agent):
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_LEGACY_ISTIOD_INSTANCE])
    check.check_id = 'test:123'

    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://localhost:8080/metrics', text=get_response('1.5', 'istiod.txt'))
        check.check(common.MOCK_LEGACY_ISTIOD_INSTANCE)

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
