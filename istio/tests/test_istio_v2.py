# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import pytest
from six import PY2

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.istio import Istio

from . import common
from .utils import _assert_tags_excluded, get_fixture_path

pytestmark = [pytest.mark.skipif(PY2, reason='Test only available on Python 3')]


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
    instance = common.MOCK_V2_MESH_INSTANCE
    instance['exclude_labels'] = common.CONFIG_EXCLUDE_LABELS
    check = Istio(common.CHECK_NAME, {}, [instance])
    dd_run_check(check)

    for metric in common.V2_MESH_METRICS:
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, common.CONFIG_EXCLUDE_LABELS)

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


@pytest.mark.parametrize(
    'exclude_labels, expected_exclude_labels',
    [
        (
            None,
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
    if exclude_labels is not None:
        instance["exclude_labels"] = exclude_labels
    check = Istio('istio', {}, [instance])
    assert check.instance["exclude_labels"] == expected_exclude_labels
