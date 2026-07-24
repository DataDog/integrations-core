# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Tests for external_dns integration.

Covers two dimensions:
- external-dns versions: v1.15.0 (legacy) vs v1.20.0
- Datadog integration versions: OpenMetrics V1 (legacy) vs OpenMetrics V2

The v1.18+ feature set (vector metrics with record_type, the http_request
summary with its reserved `host` label) is only supported by the OpenMetrics V2
implementation, so those scenarios are exercised against OMV2 only. The legacy
V1 path is kept unchanged and validated against the v1.15.0 fixture.
"""

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.external_dns import ExternalDNSCheck
from datadog_checks.external_dns.check import ExternalDNS
from datadog_checks.external_dns.metrics import COUNTER_METRICS, METRIC_MAP, construct_metrics_config

from .common import (
    CHECK_NAME,
    COUNTER_METRICS_OMV1,
    COUNTER_METRICS_OMV2,
    LEGACY_METRICS_OMV1,
    LEGACY_METRICS_OMV2,
    NAMESPACE,
    REGISTRY_ERRORS_COUNT,
    SERVICE_CHECK_OMV1,
    SERVICE_CHECK_OMV2,
    SOURCE_ERRORS_COUNT,
    V120_METRICS_OMV2,
)

pytestmark = pytest.mark.unit

SUMMARY_BASE = f'{NAMESPACE}.http.request.duration_seconds'
SUMMARY_METRIC = f'{SUMMARY_BASE}.quantile'

VECTOR_METRICS = [
    f'{NAMESPACE}.source.records',
    f'{NAMESPACE}.registry.records',
    f'{NAMESPACE}.controller.verified_records',
]

BARE_COUNTER_FIXTURE = """
    # HELP external_dns_source_errors Number of Source errors.
    # TYPE external_dns_source_errors counter
    external_dns_source_errors 7
    # HELP external_dns_registry_errors Number of Registry errors.
    # TYPE external_dns_registry_errors counter
    external_dns_registry_errors 3
    # HELP external_dns_registry_endpoints_total Number of Endpoints in the registry
    # TYPE external_dns_registry_endpoints_total gauge
    external_dns_registry_endpoints_total 10
    # HELP external_dns_source_endpoints_total Number of Endpoints in the source
    # TYPE external_dns_source_endpoints_total gauge
    external_dns_source_endpoints_total 10
"""


def _assert_error_counter_values(aggregator, counter_metrics):
    """Assert registry/source error counters are present with fixture values."""
    suffix = '.count' if counter_metrics[0].endswith('.count') else ''
    aggregator.assert_metric(f'{NAMESPACE}.registry.errors.total{suffix}', value=REGISTRY_ERRORS_COUNT)
    aggregator.assert_metric(f'{NAMESPACE}.source.errors.total{suffix}', value=SOURCE_ERRORS_COUNT)


def _run_check(instance):
    return ExternalDNSCheck(CHECK_NAME, {}, [instance])


@pytest.mark.parametrize(
    'mock_fixture,instance_fixture,expected_metrics,service_check,expect_omv2,counter_metrics',
    [
        pytest.param(
            'mock_http_response_v115',
            'instance_omv1',
            LEGACY_METRICS_OMV1,
            SERVICE_CHECK_OMV1,
            False,
            COUNTER_METRICS_OMV1,
            id='omv1-legacy',
        ),
        pytest.param(
            'mock_http_response_v115',
            'instance_omv2_counters',
            LEGACY_METRICS_OMV2,
            SERVICE_CHECK_OMV2,
            True,
            COUNTER_METRICS_OMV2,
            id='omv2-legacy',
        ),
        pytest.param(
            'mock_http_response_v120',
            'instance_omv2_counters',
            V120_METRICS_OMV2,
            SERVICE_CHECK_OMV2,
            True,
            COUNTER_METRICS_OMV2,
            id='omv2-v120',
        ),
    ],
)
def test_collect_metrics(
    aggregator,
    dd_run_check,
    request,
    mock_fixture,
    instance_fixture,
    expected_metrics,
    service_check,
    expect_omv2,
    counter_metrics,
):
    """Full metric collection for the supported OMV1/OMV2 scenarios."""
    request.getfixturevalue(mock_fixture)
    instance = request.getfixturevalue(instance_fixture)
    check = _run_check(instance)
    assert isinstance(check, ExternalDNS) is expect_omv2

    dd_run_check(check)

    for metric in expected_metrics:
        aggregator.assert_metric(metric)

    _assert_error_counter_values(aggregator, counter_metrics)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check(service_check, status=AgentCheck.OK)


@pytest.mark.parametrize(
    'values',
    [
        {'tags': ['test:tag']},
        {'prometheus_url': None, 'openmetrics_endpoint': None},
        {'prometheus_url': '', 'openmetrics_endpoint': ''},
    ],
    ids=['missing-keys', 'none-values', 'empty-strings'],
)
def test_pydantic_validator_rejects_missing_endpoint(values):
    """Pydantic validator raises ValueError when no endpoint is configured."""
    from datadog_checks.external_dns.config_models.validators import initialize_instance

    with pytest.raises(
        ValueError,
        match=r"Field `prometheus_url` or `openmetrics_endpoint` must be set",
    ):
        initialize_instance(values)


@pytest.mark.parametrize(
    'instance_fixture,service_check',
    [
        ('instance_omv1', SERVICE_CHECK_OMV1),
        ('instance_omv2', SERVICE_CHECK_OMV2),
    ],
    ids=['omv1', 'omv2'],
)
def test_service_check_ok(aggregator, mock_http_response_v115, dd_run_check, instance_fixture, service_check, request):
    """Service check is OK when endpoint is healthy."""
    instance = request.getfixturevalue(instance_fixture)
    dd_run_check(_run_check(instance))
    aggregator.assert_service_check(service_check, status=AgentCheck.OK)


@pytest.mark.parametrize(
    'instance_fixture,service_check',
    [
        ('instance_omv1', SERVICE_CHECK_OMV1),
        ('instance_omv2', SERVICE_CHECK_OMV2),
    ],
    ids=['omv1', 'omv2'],
)
def test_service_check_critical_on_failure(
    aggregator, dd_run_check, mock_http_response, instance_fixture, service_check, request
):
    """Service check is CRITICAL when endpoint returns error."""
    mock_http_response(status_code=500)
    instance = request.getfixturevalue(instance_fixture)

    with pytest.raises(Exception, match=r"HTTPError.*500 Server Error"):
        dd_run_check(_run_check(instance))

    aggregator.assert_service_check(service_check, status=AgentCheck.CRITICAL)


@pytest.mark.parametrize(
    'instance_fixture,metrics',
    [
        ('instance_omv1', LEGACY_METRICS_OMV1),
        ('instance_omv2_counters', LEGACY_METRICS_OMV2),
    ],
    ids=['omv1', 'omv2'],
)
def test_custom_tags(aggregator, mock_http_response_v115, dd_run_check, instance_fixture, metrics, request):
    """Custom tags are applied to metrics."""
    instance = request.getfixturevalue(instance_fixture)
    dd_run_check(_run_check(instance))

    for metric in metrics:
        for tag in instance['tags']:
            aggregator.assert_metric_has_tag(metric, tag)


def test_record_type_tag(aggregator, mock_http_response_v120, dd_run_check, instance_omv2):
    """Vector metrics have record_type tag (v1.20.0, OMV2 only)."""
    dd_run_check(_run_check(instance_omv2))

    for metric in VECTOR_METRICS:
        aggregator.assert_metric_has_tag(metric, 'record_type:a')


def test_host_label_renamed(aggregator, mock_http_response_v120, dd_run_check, instance_omv2):
    """The 'host' label is renamed to 'http_host' for the OpenMetrics V2 implementation."""
    dd_run_check(_run_check(instance_omv2))

    aggregator.assert_metric_has_tag(SUMMARY_METRIC, 'http_host:172.20.0.1:443')


def test_custom_renames_merge_with_default(aggregator, mock_http_response_v120, dd_run_check):
    """User-provided `rename_labels` merge with the default `host -> http_host` rename."""
    instance = {
        'openmetrics_endpoint': 'http://localhost:7979/metrics',
        'rename_labels': {'method': 'http_method'},
        'tags': ['custom:tag'],
    }
    dd_run_check(_run_check(instance))

    aggregator.assert_metric_has_tag(SUMMARY_METRIC, 'http_host:172.20.0.1:443')
    aggregator.assert_metric_has_tag(SUMMARY_METRIC, 'http_method:GET')


def test_v120_gauge_values(aggregator, mock_http_response_v120, dd_run_check, instance_omv2):
    """Gauge metric values are correctly parsed from v1.20.0 fixture (OMV2)."""
    dd_run_check(_run_check(instance_omv2))

    aggregator.assert_metric(f'{NAMESPACE}.registry.endpoints.total', value=98)
    aggregator.assert_metric(f'{NAMESPACE}.source.endpoints.total', value=19)


def test_legacy_gauge_values(aggregator, mock_http_response_v115, dd_run_check, instance_omv1):
    """Legacy gauge metric values are correctly parsed from v1.15.0 fixture."""
    dd_run_check(_run_check(instance_omv1))

    aggregator.assert_metric(f'{NAMESPACE}.registry.endpoints.total', value=333)
    aggregator.assert_metric(f'{NAMESPACE}.source.endpoints.total', value=50)
    aggregator.assert_metric(f'{NAMESPACE}.registry.a_records', value=213)


def test_summary_components(aggregator, mock_http_response_v120, dd_run_check, instance_omv2):
    """Summary metrics generate .quantile, .sum, and .count (v1.20.0, OMV2)."""
    dd_run_check(_run_check(instance_omv2))

    aggregator.assert_metric(f'{SUMMARY_BASE}.quantile')
    aggregator.assert_metric(f'{SUMMARY_BASE}.sum')
    aggregator.assert_metric(f'{SUMMARY_BASE}.count')


def test_quantile_tags(aggregator, mock_http_response_v120, dd_run_check, instance_omv2):
    """Quantile metrics have quantile tags."""
    dd_run_check(_run_check(instance_omv2))

    for quantile in ['0.5', '0.9', '0.99']:
        aggregator.assert_metric_has_tag(f'{SUMMARY_BASE}.quantile', f'quantile:{quantile}')


@pytest.mark.parametrize('instance_fixture', ['instance_omv1', 'instance_omv2'], ids=['omv1', 'omv2'])
def test_namespace_prefix(aggregator, mock_http_response_v115, dd_run_check, instance_fixture, request):
    """All metrics have external_dns namespace prefix."""
    instance = request.getfixturevalue(instance_fixture)
    dd_run_check(_run_check(instance))

    for metric_name in aggregator.metric_names:
        assert metric_name.startswith(f'{NAMESPACE}.'), f"Metric {metric_name} missing namespace prefix"


def test_construct_metrics_config_format():
    """construct_metrics_config returns correct OMV2 format."""
    metric_map = {
        'prometheus_metric': 'datadog.metric',
        'another_metric': 'another.datadog.metric',
    }

    result = construct_metrics_config(metric_map)

    assert len(result) == 2
    assert {'prometheus_metric': {'name': 'datadog.metric'}} in result
    assert {'another_metric': {'name': 'another.datadog.metric'}} in result


def test_construct_metrics_config_counter_type():
    """construct_metrics_config marks error counters with type counter."""
    metric_map = {
        'external_dns_source_errors': 'source.errors.total',
        'external_dns_registry_endpoints_total': 'registry.endpoints.total',
    }

    result = construct_metrics_config(metric_map)

    assert result == [
        {'external_dns_source_errors': {'name': 'source.errors.total', 'type': 'counter'}},
        {'external_dns_registry_endpoints_total': {'name': 'registry.endpoints.total'}},
    ]


def test_metric_map_includes_prometheus_counter_aliases():
    """METRIC_MAP keys cover Prometheus names with and without the `_total` suffix."""
    for prometheus_name in (
        'external_dns_source_errors',
        'external_dns_source_errors_total',
        'external_dns_registry_errors',
        'external_dns_registry_errors_total',
    ):
        assert prometheus_name in METRIC_MAP
        assert prometheus_name in COUNTER_METRICS


def test_construct_metrics_config_empty_input():
    """construct_metrics_config handles empty input."""
    assert construct_metrics_config({}) == []


def test_bare_counter_name_emits_once(aggregator, mock_http_response, dd_run_check, instance_omv2_counters):
    """OMV2 emits a single counter series when the exporter uses the bare name (no `_total`)."""
    mock_http_response(content=BARE_COUNTER_FIXTURE)
    dd_run_check(_run_check(instance_omv2_counters))

    aggregator.assert_metric(f'{NAMESPACE}.source.errors.total.count', value=SOURCE_ERRORS_COUNT, count=1)
    aggregator.assert_metric(f'{NAMESPACE}.registry.errors.total.count', value=REGISTRY_ERRORS_COUNT, count=1)


@pytest.mark.parametrize(
    'instance_fixture,mock_fixture,expected_metrics,submission_exclude',
    [
        pytest.param('instance_omv1', 'mock_http_response_v115', LEGACY_METRICS_OMV1, [], id='metadata-legacy'),
        pytest.param(
            'instance_omv2',
            'mock_http_response_v120',
            V120_METRICS_OMV2,
            COUNTER_METRICS_OMV2,
            id='metadata-v120',
        ),
    ],
)
def test_metadata(
    aggregator, dd_run_check, request, instance_fixture, mock_fixture, expected_metrics, submission_exclude
):
    """Submitted metrics align with metadata.csv for the matching external-dns version."""
    request.getfixturevalue(mock_fixture)
    instance = request.getfixturevalue(instance_fixture)
    dd_run_check(_run_check(instance))

    for metric in expected_metrics:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        check_metric_type=False,
        exclude=submission_exclude,
    )
