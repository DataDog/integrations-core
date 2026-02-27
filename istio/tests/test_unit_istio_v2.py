# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev import get_here
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.istio import Istio

from . import common
from .utils import _assert_tags_excluded, get_fixture_path

FIXTURE_DIR = '{}/fixtures'.format(get_here())


def test_istiod(aggregator, dd_run_check, mock_http_response):
    """
    Test the istiod deployment endpoint for V2 implementation
    """
    mock_http_response(file_path=get_fixture_path('1.5', 'istiod.txt'))
    check = Istio('istio', {}, [common.MOCK_V2_ISTIOD_INSTANCE])
    dd_run_check(check)

    for metric in common.ISTIOD_V2_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_proxy_mesh(aggregator, dd_run_check, mock_http_response):
    """
    Test proxy mesh check for V2 implementation
    """
    mock_http_response(file_path=get_fixture_path('1.5', 'istio-proxy.txt'))

    check = Istio(common.CHECK_NAME, {}, [common.MOCK_V2_MESH_INSTANCE])
    dd_run_check(check)
    for metric in common.V2_MESH_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_proxy_exclude_labels(aggregator, dd_run_check, mock_http_response):
    """
    Test proxy mesh check for V2 implementation
    """
    mock_http_response(file_path=get_fixture_path('1.5', 'istio-proxy.txt'))
    # Copy to prevent the instance in common from being overwritten
    instance = copy.copy(common.MOCK_V2_MESH_INSTANCE)
    instance['exclude_labels'] = common.CONFIG_EXCLUDE_LABELS
    check = Istio(common.CHECK_NAME, {}, [instance])
    dd_run_check(check)

    for metric in common.V2_MESH_METRICS:
        aggregator.assert_metric(metric)

    # Edited this test since v2 doesn't exclude connectionID
    _assert_tags_excluded(aggregator, common.CONFIG_EXCLUDE_LABELS, exclude_connectionid=False)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_type_override_proxy_mesh(aggregator, dd_run_check, mock_http_response):
    """
    Test proxy mesh check for V2 implementation
    """
    mock_http_response(file_path=get_fixture_path('1.5', 'istio-proxy.txt'))

    check = Istio(common.CHECK_NAME, {}, [common.MOCK_V2_MESH_OVERRIDE_INSTANCE])
    dd_run_check(check)
    # Type override should match old implementation submission names
    # Does not apply to summary/histogram
    for metric in common.V2_MESH_METRICS + common.V2_MESH_COUNTER_GAUGE:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_version_metadata(datadog_agent, dd_run_check, mock_http_response):
    """
    Test metadata version collection with V2 implementation
    """
    mock_http_response(file_path=get_fixture_path('1.5', 'istiod.txt'))
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


def test_istio_agent(aggregator, dd_run_check, mock_http_response):
    """
    Test the istiod deployment endpoint for V2 implementation
    """
    mock_http_response(file_path=get_fixture_path('1.5', 'istio-merged.txt'))
    check = Istio('istio', {}, [common.MOCK_V2_MESH_INSTANCE])
    dd_run_check(check)

    for metric in common.ISTIO_AGENT_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_istio_agent_dns_metrics(aggregator, dd_run_check, mock_http_response):
    """
    Test DNS metrics from istio-proxy merged endpoint
    """
    mock_http_response(file_path=get_fixture_path('1.5', 'istio-merged.txt'))
    check = Istio('istio', {}, [common.MOCK_V2_MESH_INSTANCE])
    dd_run_check(check)

    # Verify DNS metrics are collected
    dns_metrics = [
        'istio.mesh.agent.dns_requests.count',
        'istio.mesh.agent.dns_upstream_request_duration_seconds.bucket',
        'istio.mesh.agent.dns_upstream_request_duration_seconds.sum',
        'istio.mesh.agent.dns_upstream_request_duration_seconds.count',
    ]

    for metric in dns_metrics:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.parametrize(
    'exclude_labels, expected_exclude_labels',
    [
        (
            [
                'source_version',
                'destination_version',
                'source_canonical_revision',
                'destination_canonical_revision',
                'source_principal',
                'destination_principal',
                'source_cluster',
                'destination_cluster',
                'source_canonical_service',
                'destination_canonical_service',
                'source_workload_namespace',
                'destination_workload_namespace',
                'request_protocol',
                'connection_security_policy',
                'destination_service',
                'source_workload',
            ],
            [
                'source_version',
                'destination_version',
                'source_canonical_revision',
                'destination_canonical_revision',
                'source_principal',
                'destination_principal',
                'source_cluster',
                'destination_cluster',
                'source_canonical_service',
                'destination_canonical_service',
                'source_workload_namespace',
                'destination_workload_namespace',
                'request_protocol',
                'connection_security_policy',
                'destination_service',
                'source_workload',
            ],
        ),
        (["foo"], ["foo"]),
        ([], []),
    ],
)
def test_exclude_labels(exclude_labels, expected_exclude_labels):
    instance = copy.deepcopy(common.MOCK_V2_MESH_INSTANCE)
    instance["exclude_labels"] = exclude_labels
    check = Istio('istio', {}, [instance])
    assert check.instance["exclude_labels"] == expected_exclude_labels


def test_non_conforming_metrics(aggregator, dd_run_check, mock_http_response):
    """
    Test non conforming metrics for V2 implementation such as histograms and gauges
    ending with `_total`
    """
    mock_http_response(file_path=get_fixture_path(FIXTURE_DIR, 'non-conforming.txt'))

    check = Istio(common.CHECK_NAME, {}, [common.MOCK_V2_ISTIOD_INSTANCE])
    dd_run_check(check)

    for metric in common.NON_CONFORMING_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_unverified_metrics(aggregator, dd_run_check, mock_http_response):
    """
    Test non conforming metrics for V2 implementation such as histograms and gauges
    ending with `_total`
    """
    mock_http_response(file_path=get_fixture_path(FIXTURE_DIR, 'unverified-metrics.txt'))

    check = Istio(common.CHECK_NAME, {}, [common.MOCK_V2_ISTIOD_INSTANCE])
    dd_run_check(check)

    for metric in common.MOCK_TEST_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_all_labels_submitted(aggregator, dd_run_check, mock_http_response):
    mock_http_response(file_path=get_fixture_path(FIXTURE_DIR, 'test-labels.txt'))
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_V2_MESH_INSTANCE])
    dd_run_check(check)

    for tag in common.PREVIOUSLY_EXCLUDED_TAGS:
        aggregator.assert_metric_has_tag('istio.mesh.request.count', tag)


# --- Ambient mode (istio_mode: ambient) tests ---


def test_ambient_ztunnel_metrics(aggregator, dd_run_check, mock_http_response):
    """Test ztunnel metrics collection in ambient mode with default namespace."""
    mock_http_response(file_path=get_fixture_path('1.5', 'ztunnel.txt'))
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_V2_AMBIENT_ZTUNNEL_INSTANCE])
    dd_run_check(check)

    for metric in common.V2_ZTUNNEL_METRICS:
        aggregator.assert_metric(metric)


def test_ambient_waypoint_metrics(aggregator, dd_run_check, mock_http_response):
    """Test waypoint proxy metrics collection in ambient mode with default namespace."""
    mock_http_response(file_path=get_fixture_path('1.5', 'waypoint.txt'))
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_V2_AMBIENT_WAYPOINT_INSTANCE])
    dd_run_check(check)

    for metric in common.V2_WAYPOINT_METRICS:
        aggregator.assert_metric(metric)


def test_ambient_invalid_mode():
    """Test that invalid istio_mode raises ConfigurationError."""
    instance = {
        'istio_mode': 'invalid',
        'ztunnel_endpoint': 'http://localhost:15020/stats/prometheus',
        'use_openmetrics': True,
    }
    check = Istio(common.CHECK_NAME, {}, [instance])
    with pytest.raises(ConfigurationError, match="Invalid istio_mode 'invalid'"):
        check._parse_config()


def test_ambient_requires_at_least_one_endpoint():
    """Test that ambient mode requires at least one of ztunnel, waypoint, or istiod endpoint."""
    instance = {
        'istio_mode': 'ambient',
        'use_openmetrics': True,
    }
    check = Istio(common.CHECK_NAME, {}, [instance])
    with pytest.raises(
        ConfigurationError,
        match="In ambient mode, must specify at least one of:",
    ):
        check._parse_config()
