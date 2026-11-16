# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.crossplane import CrossplaneCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CORE_METRICS, DOC_ONLY_METRICS, PROVIDER_METRICS, get_fixture_path

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize('endpoint, expected_metrics', [('core', CORE_METRICS), ('provider', PROVIDER_METRICS)])
def test_endpoint_metrics(dd_run_check, aggregator, mock_http_response, instance, endpoint, expected_metrics):
    mock_http_response(file_path=get_fixture_path(endpoint))
    dd_run_check(CrossplaneCheck('crossplane', {}, [instance]))

    for metric in expected_metrics:
        aggregator.assert_metric(metric)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_fixtures_cover_metadata(dd_run_check, aggregator, mock_http_response, instance):
    # Catches metadata.csv rows that no mapping emits, such as a typo in either file.
    for endpoint in ('core', 'provider'):
        mock_http_response(file_path=get_fixture_path(endpoint))
        dd_run_check(CrossplaneCheck('crossplane', {}, [instance]))

    missing = set(get_metadata_metrics()) - DOC_ONLY_METRICS - set(aggregator.metric_names)
    assert not missing, sorted(missing)


@pytest.mark.parametrize(
    'metric, renamed_prefix, reserved_prefix',
    [
        ('crossplane.rest_client.requests.count', 'rest_client_host:', 'host:'),
        ('crossplane.go.info', 'go_version:', 'version:'),
    ],
)
def test_reserved_labels_renamed(
    dd_run_check, aggregator, mock_http_response, instance, metric, renamed_prefix, reserved_prefix
):
    mock_http_response(file_path=get_fixture_path('core'))
    dd_run_check(CrossplaneCheck('crossplane', {}, [instance]))

    aggregator.assert_metric_has_tag_prefix(metric, renamed_prefix)
    for stub in aggregator.metrics(metric):
        assert not any(tag.startswith(reserved_prefix) for tag in stub.tags), stub.tags


def test_health_service_check_cannot_be_enabled(dd_run_check, aggregator, mock_http_response, instance):
    mock_http_response(file_path=get_fixture_path('core'))
    dd_run_check(CrossplaneCheck('crossplane', {}, [{**instance, 'enable_health_service_check': True}]))

    aggregator.assert_service_check('crossplane.openmetrics.health', count=0)
