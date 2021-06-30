# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from six import PY2

from datadog_checks.istio import Istio

from . import common
from .utils import _assert_tags_excluded, get_fixture_path


@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
def test_istiod(aggregator, dd_run_check, mock_http_response):
    """
    Test the istiod deployment endpoint for V2 implementation
    """
    mock_http_response(file_path=get_fixture_path('1.5', 'istiod.txt'))
    check = Istio('istio', {}, [common.MOCK_V2_ISTIOD_INSTANCE])
    dd_run_check(check)

    for metric in common.ISTIOD_V2_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
def test_proxy_mesh(aggregator, dd_run_check, mock_http_response):
    """
    Test proxy mesh check for V2 implementation
    """
    mock_http_response(file_path=get_fixture_path('1.5', 'istio-proxy.txt'))

    check = Istio(common.CHECK_NAME, {}, [common.MOCK_V2_MESH_INSTANCE])
    dd_run_check(check)
    for metric in common.V2_MESH_METRICS:
        if metric.endswith('.total'):
            metric = '{}'.format(metric[:-6])
        aggregator.assert_metric(metric)

    _assert_tags_excluded(aggregator, [])

    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
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

