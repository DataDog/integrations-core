# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from six import PY2

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.istio import Istio

from . import common
from .utils import _assert_tags_excluded

@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
def test_istiod(aggregator, dd_run_check,  istiod_mixture_fixture):
    """
    Test the istiod deployment endpoint for v1.5+ check
    """
    check = Istio('istio', {}, [common.MOCK_V2_ISTIOD_INSTANCE])
    dd_run_check(check)

    for metric in common.ISTIOD_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_legacy_istiod(aggregator, istiod_mixture_fixture):
    """
    Test the istiod deployment endpoint for v1.5+ check
    """
    check = Istio('istio', {}, [common.MOCK_LEGACY_ISTIOD_INSTANCE])
    check.check(common.MOCK_LEGACY_ISTIOD_INSTANCE)

    for metric in common.ISTIOD_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_proxy_mesh(aggregator, istio_proxy_mesh_fixture):
    """
    Test proxy mesh check
    """
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_ISTIO_PROXY_MESH_INSTANCE])
    check.check(common.MOCK_ISTIO_PROXY_MESH_INSTANCE)

    for metric in common.MESH_METRICS + common.MESH_MERICS_1_5:
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, [])

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
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

    _assert_tags_excluded(aggregator, exclude_tags)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_legacy_version_metadata(datadog_agent, istiod_mixture_fixture):
    check = Istio(common.CHECK_NAME, {}, [common.MOCK_LEGACY_ISTIOD_INSTANCE])
    check.check_id = 'test:123'
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
