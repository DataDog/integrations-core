# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Tests for external_dns integration.

Covers two dimensions:
- external-dns versions: v1.15.0 (legacy) vs v1.20.0
- Datadog integration versions: OpenMetrics V1 (legacy) vs OpenMetrics V2

Test matrix:
+------------------+------------------+------------------+
|                  | external-dns     | external-dns     |
|                  | v1.15.0 (legacy) | v1.20.0          |
+------------------+------------------+------------------+
| OpenMetrics V1   | test_omv1_v115   | test_omv1_v120   |
+------------------+------------------+------------------+
| OpenMetrics V2   | test_omv2_v115   | test_omv2_v120   |
+------------------+------------------+------------------+
"""

import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
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
    LEGACY_ONLY_METADATA_METRICS,
    NAMESPACE,
    REGISTRY_ERRORS_COUNT,
    SOURCE_ERRORS_COUNT,
    V120_METRICS_OMV1,
    V120_METRICS_OMV2,
    V120_ONLY_METADATA_METRICS,
)

pytestmark = pytest.mark.unit

SERVICE_CHECK_OMV1 = f'{NAMESPACE}.prometheus.health'
SERVICE_CHECK_OMV2 = f'{NAMESPACE}.openmetrics.health'

METRIC_COLLECTION_CASES = [
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
        'instance_omv1',
        V120_METRICS_OMV1,
        SERVICE_CHECK_OMV1,
        False,
        COUNTER_METRICS_OMV1,
        id='omv1-v120',
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
]

METADATA_CASES = [
    pytest.param(
        'mock_http_response_v115',
        LEGACY_METRICS_OMV1,
        V120_ONLY_METADATA_METRICS,
        id='metadata-legacy',
    ),
    pytest.param(
        'mock_http_response_v120',
        V120_METRICS_OMV1,
        LEGACY_ONLY_METADATA_METRICS,
        id='metadata-v120',
    ),
]


def _assert_error_counter_values(aggregator, counter_metrics):
    """Assert registry/source error counters are present with fixture values."""
    suffix = '.count' if counter_metrics[0].endswith('.count') else ''
    aggregator.assert_metric(f'{NAMESPACE}.registry.errors.total{suffix}', value=REGISTRY_ERRORS_COUNT)
    aggregator.assert_metric(f'{NAMESPACE}.source.errors.total{suffix}', value=SOURCE_ERRORS_COUNT)


def _run_check(instance):
    return ExternalDNSCheck(CHECK_NAME, {}, [instance])


class TestMetricCollection:
    """Full metric collection for the OMV1/OMV2 × legacy/v1.20 matrix."""

    @pytest.mark.parametrize(
        'mock_fixture,instance_fixture,expected_metrics,service_check,expect_omv2,counter_metrics',
        METRIC_COLLECTION_CASES,
    )
    def test_collect_metrics(
        self,
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


class TestConfigurationErrors:
    """Verify configuration error handling."""

    @pytest.mark.parametrize(
        'instance',
        [
            {'tags': ['test:tag']},
            {},
        ],
        ids=['missing-endpoint', 'empty-instance'],
    )
    def test_missing_endpoint_raises_error(self, instance):
        """Missing prometheus_url raises ConfigurationError for OMV1."""
        with pytest.raises(ConfigurationError, match="Unable to find prometheus endpoint"):
            ExternalDNSCheck(CHECK_NAME, {}, [instance])

    @pytest.mark.parametrize(
        'values',
        [
            {'tags': ['test:tag']},
            {'prometheus_url': None, 'openmetrics_endpoint': None},
            {'prometheus_url': '', 'openmetrics_endpoint': ''},
        ],
        ids=['missing-keys', 'none-values', 'empty-strings'],
    )
    def test_pydantic_validator_rejects_missing_endpoint(self, values):
        """Pydantic validator raises ValueError when no endpoint is configured."""
        from datadog_checks.external_dns.config_models.validators import initialize_instance

        with pytest.raises(
            ValueError,
            match=r"Field `prometheus_url` or `openmetrics_endpoint` must be set",
        ):
            initialize_instance(values)


class TestServiceCheck:
    """Verify service check behavior for both integration versions."""

    @pytest.mark.parametrize(
        'instance_fixture,service_check',
        [
            ('instance_omv1', SERVICE_CHECK_OMV1),
            ('instance_omv2', SERVICE_CHECK_OMV2),
        ],
        ids=['omv1', 'omv2'],
    )
    def test_service_check_ok(
        self, aggregator, mock_http_response_v115, dd_run_check, instance_fixture, service_check, request
    ):
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
        self, aggregator, dd_run_check, mock_http_response, instance_fixture, service_check, request
    ):
        """Service check is CRITICAL when endpoint returns error."""
        mock_http_response(status_code=500)
        instance = request.getfixturevalue(instance_fixture)

        with pytest.raises(Exception, match=r"HTTPError.*500 Server Error"):
            dd_run_check(_run_check(instance))

        aggregator.assert_service_check(service_check, status=AgentCheck.CRITICAL)


class TestTags:
    """Verify custom tags are applied correctly."""

    @pytest.mark.parametrize(
        'instance_fixture,metrics',
        [
            ('instance_omv1', LEGACY_METRICS_OMV1),
            ('instance_omv2_counters', LEGACY_METRICS_OMV2),
        ],
        ids=['omv1', 'omv2'],
    )
    def test_custom_tags(self, aggregator, mock_http_response_v115, dd_run_check, instance_fixture, metrics, request):
        """Custom tags are applied to metrics."""
        instance = request.getfixturevalue(instance_fixture)
        dd_run_check(_run_check(instance))

        for metric in metrics:
            for tag in instance['tags']:
                aggregator.assert_metric_has_tag(metric, tag)


class TestV120Labels:
    """Verify record_type label is converted to tag for v1.20.0 vector metrics."""

    VECTOR_METRICS = [
        f'{NAMESPACE}.source.records',
        f'{NAMESPACE}.registry.records',
        f'{NAMESPACE}.controller.verified_records',
    ]

    @pytest.mark.parametrize('instance_fixture', ['instance_omv1', 'instance_omv2'], ids=['omv1', 'omv2'])
    def test_record_type_tag(self, aggregator, mock_http_response_v120, dd_run_check, instance_fixture, request):
        """Vector metrics have record_type tag."""
        instance = request.getfixturevalue(instance_fixture)
        dd_run_check(_run_check(instance))

        for metric in self.VECTOR_METRICS:
            aggregator.assert_metric_has_tag(metric, 'record_type:a')


class TestLabelRenaming:
    """Verify reserved label renaming (host -> http_host)."""

    SUMMARY_METRIC = f'{NAMESPACE}.http.request.duration_seconds.quantile'

    @pytest.mark.parametrize('instance_fixture', ['instance_omv1', 'instance_omv2'], ids=['omv1', 'omv2'])
    def test_host_label_renamed(self, aggregator, mock_http_response_v120, dd_run_check, instance_fixture, request):
        """The 'host' label is renamed to 'http_host'."""
        instance = request.getfixturevalue(instance_fixture)
        dd_run_check(_run_check(instance))

        aggregator.assert_metric_has_tag(self.SUMMARY_METRIC, 'http_host:172.20.0.1:443')

    @pytest.mark.parametrize(
        'endpoint_key,rename_key',
        [
            ('prometheus_url', 'labels_mapper'),
            ('openmetrics_endpoint', 'labels_mapper'),
            ('openmetrics_endpoint', 'rename_labels'),
        ],
        ids=['omv1-labels_mapper', 'omv2-legacy-labels_mapper', 'omv2-native-rename_labels'],
    )
    def test_custom_renames_merge_with_default(
        self, aggregator, mock_http_response_v120, dd_run_check, endpoint_key, rename_key
    ):
        """
        User-provided renames merge with the default `host -> http_host` rename across OMV1/OMV2
        and legacy/native keys.
        """
        instance = {
            endpoint_key: 'http://localhost:7979/metrics',
            rename_key: {'method': 'http_method'},
            'tags': ['custom:tag'],
        }
        dd_run_check(_run_check(instance))

        aggregator.assert_metric_has_tag(self.SUMMARY_METRIC, 'http_host:172.20.0.1:443')
        aggregator.assert_metric_has_tag(self.SUMMARY_METRIC, 'http_method:GET')


class TestMetricValues:
    """Verify selected gauge values are correctly parsed from fixtures."""

    @pytest.mark.parametrize('instance_fixture', ['instance_omv1', 'instance_omv2'], ids=['omv1', 'omv2'])
    def test_v120_gauge_values(self, aggregator, mock_http_response_v120, dd_run_check, instance_fixture, request):
        """Gauge metric values are correctly parsed from v1.20.0 fixture."""
        instance = request.getfixturevalue(instance_fixture)
        dd_run_check(_run_check(instance))

        aggregator.assert_metric(f'{NAMESPACE}.registry.endpoints.total', value=98)
        aggregator.assert_metric(f'{NAMESPACE}.source.endpoints.total', value=19)

    def test_legacy_gauge_values(self, aggregator, mock_http_response_v115, dd_run_check, instance_omv1):
        """Legacy gauge metric values are correctly parsed from v1.15.0 fixture."""
        dd_run_check(_run_check(instance_omv1))

        aggregator.assert_metric(f'{NAMESPACE}.registry.endpoints.total', value=333)
        aggregator.assert_metric(f'{NAMESPACE}.source.endpoints.total', value=50)
        aggregator.assert_metric(f'{NAMESPACE}.registry.a_records', value=213)


class TestSummaryMetrics:
    """Verify summary metric components are correctly collected."""

    SUMMARY_BASE = f'{NAMESPACE}.http.request.duration_seconds'

    @pytest.mark.parametrize('instance_fixture', ['instance_omv1', 'instance_omv2'], ids=['omv1', 'omv2'])
    def test_summary_components(self, aggregator, mock_http_response_v120, dd_run_check, instance_fixture, request):
        """Summary metrics generate .quantile, .sum, and .count."""
        instance = request.getfixturevalue(instance_fixture)
        dd_run_check(_run_check(instance))

        aggregator.assert_metric(f'{self.SUMMARY_BASE}.quantile')
        aggregator.assert_metric(f'{self.SUMMARY_BASE}.sum')
        aggregator.assert_metric(f'{self.SUMMARY_BASE}.count')

    def test_quantile_tags(self, aggregator, mock_http_response_v120, dd_run_check, instance_omv1):
        """Quantile metrics have quantile tags."""
        dd_run_check(_run_check(instance_omv1))

        for quantile in ['0.5', '0.9', '0.99']:
            aggregator.assert_metric_has_tag(f'{self.SUMMARY_BASE}.quantile', f'quantile:{quantile}')


class TestNamespace:
    """Verify all metrics have the correct namespace prefix."""

    @pytest.mark.parametrize('instance_fixture', ['instance_omv1', 'instance_omv2'], ids=['omv1', 'omv2'])
    def test_namespace_prefix(self, aggregator, mock_http_response_v115, dd_run_check, instance_fixture, request):
        """All metrics have external_dns namespace prefix."""
        instance = request.getfixturevalue(instance_fixture)
        dd_run_check(_run_check(instance))

        for metric_name in aggregator.metric_names:
            assert metric_name.startswith(f'{NAMESPACE}.'), f"Metric {metric_name} missing namespace prefix"


class TestConstructMetricsConfig:
    """Unit tests for construct_metrics_config function."""

    def test_format(self):
        """construct_metrics_config returns correct OMV2 format."""
        metric_map = {
            'prometheus_metric': 'datadog.metric',
            'another_metric': 'another.datadog.metric',
        }

        result = construct_metrics_config(metric_map)

        assert len(result) == 2
        assert {'prometheus_metric': {'name': 'datadog.metric'}} in result
        assert {'another_metric': {'name': 'another.datadog.metric'}} in result

    def test_counter_type(self):
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

    def test_metric_map_includes_prometheus_counter_aliases(self):
        """METRIC_MAP keys cover Prometheus names with and without the `_total` suffix."""
        for prometheus_name in (
            'external_dns_source_errors',
            'external_dns_source_errors_total',
            'external_dns_registry_errors',
            'external_dns_registry_errors_total',
        ):
            assert prometheus_name in METRIC_MAP
            assert prometheus_name in COUNTER_METRICS

    def test_empty_input(self):
        """construct_metrics_config handles empty input."""
        assert construct_metrics_config({}) == []


class TestCounterAliases:
    """Verify counter name aliases (`_total` suffix vs bare) emit a single series."""

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

    def test_bare_counter_name_emits_once(self, aggregator, mock_http_response, dd_run_check, instance_omv2_counters):
        """OMV2 emits a single counter series when the exporter uses the bare name (no `_total`)."""
        mock_http_response(content=self.BARE_COUNTER_FIXTURE)
        dd_run_check(_run_check(instance_omv2_counters))

        aggregator.assert_metric(f'{NAMESPACE}.source.errors.total.count', value=SOURCE_ERRORS_COUNT, count=1)
        aggregator.assert_metric(f'{NAMESPACE}.registry.errors.total.count', value=REGISTRY_ERRORS_COUNT, count=1)


class TestMetadata:
    """Verify submitted metrics match metadata.csv."""

    @staticmethod
    def _metadata_metrics(exclude):
        return {name: row for name, row in get_metadata_metrics().items() if name not in exclude}

    @pytest.mark.parametrize('mock_fixture,expected_metrics,metadata_exclude', METADATA_CASES)
    def test_metadata(
        self, aggregator, dd_run_check, instance_omv1, request, mock_fixture, expected_metrics, metadata_exclude
    ):
        """Fixture metrics align with metadata.csv for the matching external-dns version."""
        request.getfixturevalue(mock_fixture)
        dd_run_check(_run_check(instance_omv1))

        for metric in expected_metrics:
            aggregator.assert_metric(metric)

        aggregator.assert_all_metrics_covered()
        aggregator.assert_metrics_using_metadata(
            self._metadata_metrics(metadata_exclude),
            check_submission_type=True,
            check_metric_type=False,
            check_symmetric_inclusion=True,
        )
