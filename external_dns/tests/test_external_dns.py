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
from datadog_checks.external_dns import ExternalDNSCheck
from datadog_checks.external_dns.check import ExternalDNS
from datadog_checks.external_dns.metrics import construct_metrics_config

from .common import (
    CHECK_NAME,
    LEGACY_COUNTER_METRICS,
    LEGACY_METRICS_OMV1,
    LEGACY_METRICS_OMV2,
    NAMESPACE,
    V120_COUNTER_METRICS,
    V120_METRICS_OMV1,
    V120_METRICS_OMV2,
)

# Service check names
SERVICE_CHECK_OMV1 = f'{NAMESPACE}.prometheus.health'
SERVICE_CHECK_OMV2 = f'{NAMESPACE}.openmetrics.health'


class TestExternalDNSv115:
    """Tests for external-dns v1.15.0 (legacy) with separate a_records/aaaa_records."""

    def test_omv1_v115(self, aggregator, mock_http_response_v115, dd_run_check, instance_omv1):
        """OpenMetrics V1 + external-dns v1.15.0: all metrics including zero-value counters."""
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance_omv1])
        assert not isinstance(check, ExternalDNS), "Should use legacy OpenMetricsBaseCheck"

        dd_run_check(check)

        for metric in LEGACY_METRICS_OMV1:
            aggregator.assert_metric(metric)

        aggregator.assert_all_metrics_covered()
        aggregator.assert_service_check(SERVICE_CHECK_OMV1, status=AgentCheck.OK)

    def test_omv2_v115(self, aggregator, mock_http_response_v115, dd_run_check, instance_omv2):
        """OpenMetrics V2 + external-dns v1.15.0: gauges only (counters=0 not submitted)."""
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance_omv2])
        assert isinstance(check, ExternalDNS), "Should use OpenMetricsBaseCheckV2"

        dd_run_check(check)
        dd_run_check(check)

        for metric in LEGACY_METRICS_OMV2:
            aggregator.assert_metric(metric)

        for metric in LEGACY_COUNTER_METRICS:
            aggregator.assert_metric(metric, count=0)

        aggregator.assert_all_metrics_covered()
        aggregator.assert_service_check(SERVICE_CHECK_OMV2, status=AgentCheck.OK)


class TestExternalDNSv120:
    """Tests for external-dns v1.20.0 with vector metrics (record_type label)."""

    def test_omv1_v120(self, aggregator, mock_http_response_v120, dd_run_check, instance_omv1):
        """OpenMetrics V1 + external-dns v1.20.0: all metrics including summary and counters."""
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance_omv1])
        assert not isinstance(check, ExternalDNS), "Should use legacy OpenMetricsBaseCheck"

        dd_run_check(check)

        for metric in V120_METRICS_OMV1:
            aggregator.assert_metric(metric)

        aggregator.assert_all_metrics_covered()
        aggregator.assert_service_check(SERVICE_CHECK_OMV1, status=AgentCheck.OK)

    def test_omv2_v120(self, aggregator, mock_http_response_v120, dd_run_check, instance_omv2):
        """OpenMetrics V2 + external-dns v1.20.0: gauges and summary (counters=0 not submitted)."""
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance_omv2])
        assert isinstance(check, ExternalDNS), "Should use OpenMetricsBaseCheckV2"

        dd_run_check(check)
        dd_run_check(check)

        for metric in V120_METRICS_OMV2:
            aggregator.assert_metric(metric)

        for metric in V120_COUNTER_METRICS:
            aggregator.assert_metric(metric, count=0)

        aggregator.assert_all_metrics_covered()
        aggregator.assert_service_check(SERVICE_CHECK_OMV2, status=AgentCheck.OK)


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

    def test_pydantic_validator_rejects_missing_endpoint(self):
        """Pydantic validator raises ValueError for missing endpoints."""
        from datadog_checks.external_dns.config_models.validators import initialize_instance

        with pytest.raises(ValueError, match="prometheus_url.*openmetrics_endpoint"):
            initialize_instance({'tags': ['test:tag']})


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
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)
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
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance])

        with pytest.raises(Exception):
            dd_run_check(check)

        aggregator.assert_service_check(service_check, status=AgentCheck.CRITICAL)


class TestTags:
    """Verify custom tags are applied correctly."""

    @pytest.mark.parametrize(
        'instance_fixture,metrics',
        [
            ('instance_omv1', LEGACY_METRICS_OMV1),
            ('instance_omv2', LEGACY_METRICS_OMV2),
        ],
        ids=['omv1', 'omv2'],
    )
    def test_custom_tags(self, aggregator, mock_http_response_v115, dd_run_check, instance_fixture, metrics, request):
        """Custom tags are applied to metrics."""
        instance = request.getfixturevalue(instance_fixture)
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)

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
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)

        for metric in self.VECTOR_METRICS:
            aggregator.assert_metric_has_tag(metric, 'record_type:a')


class TestLabelRenaming:
    """Verify reserved label renaming (host -> http_host)."""

    SUMMARY_METRIC = f'{NAMESPACE}.http.request.duration_seconds.quantile'

    @pytest.mark.parametrize('instance_fixture', ['instance_omv1', 'instance_omv2'], ids=['omv1', 'omv2'])
    def test_host_label_renamed(self, aggregator, mock_http_response_v120, dd_run_check, instance_fixture, request):
        """The 'host' label is renamed to 'http_host'."""
        instance = request.getfixturevalue(instance_fixture)
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)

        aggregator.assert_metric_has_tag(self.SUMMARY_METRIC, 'http_host:172.20.0.1:443')

    def test_omv1_custom_labels_mapper(self, aggregator, mock_http_response_v120, dd_run_check):
        """Custom labels_mapper is merged with default host renaming for OMV1."""
        instance = {
            'prometheus_url': 'http://localhost:7979/metrics',
            'labels_mapper': {'method': 'http_method'},
            'tags': ['custom:tag'],
        }
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)

        aggregator.assert_metric_has_tag(self.SUMMARY_METRIC, 'http_host:172.20.0.1:443')
        aggregator.assert_metric_has_tag(self.SUMMARY_METRIC, 'http_method:GET')


class TestMetricValues:
    """Verify metric values are correctly parsed from fixtures."""

    @pytest.mark.parametrize('instance_fixture', ['instance_omv1', 'instance_omv2'], ids=['omv1', 'omv2'])
    def test_v120_gauge_values(self, aggregator, mock_http_response_v120, dd_run_check, instance_fixture, request):
        """Gauge metric values are correctly parsed from v1.20.0 fixture."""
        instance = request.getfixturevalue(instance_fixture)
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)

        aggregator.assert_metric(f'{NAMESPACE}.registry.endpoints.total', value=98)
        aggregator.assert_metric(f'{NAMESPACE}.source.endpoints.total', value=19)

    def test_legacy_gauge_values(self, aggregator, mock_http_response_v115, dd_run_check, instance_omv1):
        """Legacy gauge metric values are correctly parsed from v1.15.0 fixture."""
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance_omv1])
        dd_run_check(check)

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
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)

        aggregator.assert_metric(f'{self.SUMMARY_BASE}.quantile')
        aggregator.assert_metric(f'{self.SUMMARY_BASE}.sum')
        aggregator.assert_metric(f'{self.SUMMARY_BASE}.count')

    def test_quantile_tags(self, aggregator, mock_http_response_v120, dd_run_check, instance_omv1):
        """Quantile metrics have quantile tags."""
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance_omv1])
        dd_run_check(check)

        for quantile in ['0.5', '0.9', '0.99']:
            aggregator.assert_metric_has_tag(f'{self.SUMMARY_BASE}.quantile', f'quantile:{quantile}')


class TestNamespace:
    """Verify all metrics have the correct namespace prefix."""

    @pytest.mark.parametrize('instance_fixture', ['instance_omv1', 'instance_omv2'], ids=['omv1', 'omv2'])
    def test_namespace_prefix(self, aggregator, mock_http_response_v115, dd_run_check, instance_fixture, request):
        """All metrics have external_dns namespace prefix."""
        instance = request.getfixturevalue(instance_fixture)
        check = ExternalDNSCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)

        for metric_name in aggregator._metrics:
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

    def test_empty_input(self):
        """construct_metrics_config handles empty input."""
        assert construct_metrics_config({}) == []
