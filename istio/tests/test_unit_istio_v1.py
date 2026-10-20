# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.istio import Istio

from . import common
from .utils import _assert_tags_excluded, get_response


def test_legacy_istiod(aggregator, dd_run_check, fake_http_response):
    """
    Test the istiod deployment endpoint for v1.5+ check for OpenMetricsV1 implementation
    """
    fake_http_response(
        common.MOCK_LEGACY_ISTIOD_INSTANCE['istiod_endpoint'],
        get_response('1.5', 'istiod.txt'),
        headers={'Content-Type': 'text/plain'},
    )
    check = Istio('istio', {}, [common.MOCK_LEGACY_ISTIOD_INSTANCE])
    dd_run_check(check)

    for metric in common.ISTIOD_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_legacy_proxy_mesh(aggregator, dd_run_check, fake_http_response):
    """
    Test proxy mesh check for OpenMetricsV1 implementation
    """
    fake_http_response(
        common.MOCK_LEGACY_MESH_INSTANCE['istio_mesh_endpoint'],
        get_response('1.5', 'istio-proxy.txt'),
        headers={'Content-Type': 'text/plain'},
    )
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_LEGACY_MESH_INSTANCE])
    dd_run_check(check)

    for metric in common.LEGACY_MESH_METRICS + common.MESH_MERICS_1_5:
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, [], exclude_connectionid=True)

    aggregator.assert_all_metrics_covered()


def test_legacy_proxy_mesh_exclude(aggregator, dd_run_check, fake_http_response):
    """
    Test proxy mesh check for OpenMetricsV1 implementation
    """
    fake_http_response(
        common.MOCK_LEGACY_MESH_INSTANCE['istio_mesh_endpoint'],
        get_response('1.5', 'istio-proxy.txt'),
        headers={'Content-Type': 'text/plain'},
    )
    exclude_tags = ['destination_app', 'destination_principal']
    instance = common.MOCK_LEGACY_MESH_INSTANCE
    instance['exclude_labels'] = exclude_tags

    check = Istio(common.CHECK_NAME, {}, [instance])
    dd_run_check(check)

    for metric in common.LEGACY_MESH_METRICS + common.MESH_MERICS_1_5:
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, exclude_tags, exclude_connectionid=True)

    aggregator.assert_all_metrics_covered()


def test_legacy_version_metadata(datadog_agent, dd_run_check, fake_http_response):
    fake_http_response(
        common.MOCK_LEGACY_ISTIOD_INSTANCE['istiod_endpoint'],
        get_response('1.5', 'istiod.txt'),
        headers={'Content-Type': 'text/plain'},
    )
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_LEGACY_ISTIOD_INSTANCE])
    check.check_id = 'test:123'
    dd_run_check(check)

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
