# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from prometheus_client.samples import Sample

from datadog_checks.kube_apiserver_metrics import KubeAPIServerMetricsCheck
from datadog_checks.kube_apiserver_metrics.sli_metrics import SliMetricsScraperMixin

pytestmark = pytest.mark.unit

CHECK_NAME = "kube_apiserver"


class FakeMetric:
    def __init__(self, samples, name=None, metric_type=None):
        self.samples = samples
        self.name = name
        self.type = metric_type


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at kube_apiserver_metrics.py:98 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert KubeAPIServerMetricsCheck.DEFAULT_METRIC_LIMIT == 0


def test_default_ssl_verify_and_bearer_token_auth_class_defaults():
    # Kills the core/ReplaceFalseWithTrue mutant at kube_apiserver_metrics.py:102 (DEFAULT_SSL_VERIFY)
    # and the core/ReplaceTrueWithFalse mutant at kube_apiserver_metrics.py:103 (DEFAULT_BEARER_TOKEN_AUTH).
    assert KubeAPIServerMetricsCheck.DEFAULT_SSL_VERIFY is False
    assert KubeAPIServerMetricsCheck.DEFAULT_BEARER_TOKEN_AUTH is True


def test_constructor_skips_instance_processing_when_instances_is_none():
    # Kills the core/ReplaceComparisonOperator_IsNot_Is and AddNot mutants at kube_apiserver_metrics.py:134
    # (`if instances is not None:` flipped would try to iterate over None and raise TypeError).
    KubeAPIServerMetricsCheck(CHECK_NAME, {}, None)


def test_health_url_computed_from_prometheus_url_when_missing():
    # Kills the core/ZeroIterationForLoop mutant at kube_apiserver_metrics.py:135
    # (`for instance in instances:` -> `for instance in []`), which would leave health_url unset.
    instance = {
        'prometheus_url': 'https://localhost:443/metrics',
        'bearer_token_auth': 'false',
        'slis_available': True,
    }
    KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    assert instance['health_url'] == 'https://localhost:443/healthz'


def test_health_url_left_untouched_when_already_set():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot, AddNot, and ReplaceAndWithOr mutants at
    # kube_apiserver_metrics.py:139 (`if url is None and search(...)`), which would overwrite an explicit health_url.
    instance = {
        'prometheus_url': 'https://localhost:443/metrics',
        'bearer_token_auth': 'false',
        'health_url': 'https://localhost:443/custom-health',
        'slis_available': True,
    }
    KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    assert instance['health_url'] == 'https://localhost:443/custom-health'


def test_create_instance_only_prepends_scheme_when_endpoint_has_none(instance):
    # Kills the core/ReplaceUnaryOperator_Delete_Not and core/AddNot mutants at kube_apiserver_metrics.py:179
    # (`if not match('^https?://.*$', endpoint):`), which would flip when the scheme gets prepended.
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    with_scheme = check._create_kube_apiserver_metrics_instance({'prometheus_url': 'https://localhost:443/metrics'})
    assert with_scheme['prometheus_url'] == 'https://localhost:443/metrics'

    without_scheme = check._create_kube_apiserver_metrics_instance({'prometheus_url': 'localhost:443/metrics'})
    assert without_scheme['prometheus_url'] == 'https://localhost:443/metrics'


def test_submit_metric_defaults_to_submitting_monotonic_count(aggregator, instance):
    # Kills the core/ReplaceTrueWithFalse mutant at kube_apiserver_metrics.py:195
    # (`def submit_metric(..., monotonic_count=True):` default argument).
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    metric = FakeMetric([(None, {}, 5.0)])
    scraper_config = {'namespace': 'kube_apiserver', 'custom_tags': []}
    check.submit_metric('.custom_metric', metric, scraper_config)
    aggregator.assert_metric('kube_apiserver.custom_metric.count', count=1)


def test_slis_available_not_overwritten_when_already_set():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and AddNot mutants at kube_apiserver_metrics.py:146
    # (`if instance.get('slis_available') is None:`), which would re-run detection over a pre-set value.
    instance = {
        'prometheus_url': 'https://localhost:443/metrics',
        'bearer_token_auth': 'false',
        'slis_available': False,
    }
    with mock.patch.object(SliMetricsScraperMixin, 'detect_sli_endpoint', return_value=True):
        KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    assert instance['slis_available'] is False


def test_sli_metrics_processed_only_when_scraper_config_and_available_both_true(instance):
    # Kills the core/AddNot mutant at kube_apiserver_metrics.py:160
    # (`if instance.get('sli_scraper_config') and instance.get('slis_available'):`).
    instance['slis_available'] = True
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    check.process = mock.MagicMock()
    check.check(instance)
    assert check.process.call_count == 2


def test_sli_metrics_skipped_when_not_available_even_if_scraper_config_present(instance):
    # Kills the core/ReplaceAndWithOr mutant at kube_apiserver_metrics.py:160
    # (`... and instance.get('slis_available')` -> `... or instance.get('slis_available')`).
    instance['slis_available'] = False
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    check.process = mock.MagicMock()
    check.check(instance)
    assert check.process.call_count == 1


def test_submit_metric_includes_sample_label_tags(aggregator, instance):
    # Kills the core/ZeroIterationForLoop mutant at kube_apiserver_metrics.py:204
    # (`for label_name, label_value in sample[self.SAMPLE_LABELS].items():` -> `for ... in []`).
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    metric = FakeMetric([(None, {'pod': 'foo'}, 5.0)])
    scraper_config = {'namespace': 'kube_apiserver', 'custom_tags': []}
    check.submit_metric('.custom_metric', metric, scraper_config)
    aggregator.assert_metric_has_tag('kube_apiserver.custom_metric', 'pod:foo')


def test_aggregator_unavailable_apiservice_renames_tag_and_skips_monotonic_count(aggregator, instance):
    # Kills the core/ZeroIterationForLoop mutant at kube_apiserver_metrics.py:218 and the
    # core/ReplaceFalseWithTrue mutant at kube_apiserver_metrics.py:220 (monotonic_count default).
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    metric = FakeMetric([(None, {'name': 'kube-dns'}, 1.0)])
    scraper_config = {'namespace': 'kube_apiserver', 'custom_tags': []}
    check.aggregator_unavailable_apiservice(metric, scraper_config)
    aggregator.assert_metric_has_tag('kube_apiserver.aggregator_unavailable_apiservice', 'apiservice_name:kube-dns')
    aggregator.assert_metric('kube_apiserver.aggregator_unavailable_apiservice.count', count=0)


def test_detect_sli_endpoint_returns_false_on_request_error(instance):
    # Kills the core/ReplaceFalseWithTrue mutant at sli_metrics.py:59 (`return False` in the except block).
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    check._slis_available = None
    handler = mock.MagicMock()
    handler.get.side_effect = Exception("boom")
    assert check.detect_sli_endpoint(handler, "https://localhost:443/metrics/slis") is False


def test_detect_sli_endpoint_uses_streaming_request(instance):
    # Kills the core/ReplaceTrueWithFalse mutant at sli_metrics.py:56 (`http_handler.get(url, stream=True)`).
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    check._slis_available = None
    handler = mock.MagicMock()
    handler.get.return_value = mock.MagicMock(status_code=200)
    check.detect_sli_endpoint(handler, "https://localhost:443/metrics/slis")
    handler.get.assert_called_once_with("https://localhost:443/metrics/slis", stream=True)


def test_detect_sli_endpoint_caches_result_and_skips_second_request(instance):
    # Kills the core/ReplaceComparisonOperator_IsNot_Is and AddNot mutants at sli_metrics.py:53
    # (`if self._slis_available is not None:`), which would re-query instead of returning the cached value.
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    check._slis_available = None
    handler = mock.MagicMock()
    handler.get.return_value = mock.MagicMock(status_code=200)
    assert check.detect_sli_endpoint(handler, "https://localhost:443/metrics/slis") is True
    handler.get.reset_mock()
    assert check.detect_sli_endpoint(handler, "https://localhost:443/metrics/slis") is True
    handler.get.assert_not_called()


def test_detect_sli_endpoint_logs_permission_hint_only_at_403(instance):
    # Kills the core/ReplaceComparisonOperator_Eq_* (NotEq/Lt/LtE/Gt/GtE), AddNot, and NumberReplacer
    # mutants at sli_metrics.py:60 (`if r.status_code == 403:`).
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    for status_code, expect_logged in [(403, True), (402, False), (404, False)]:
        check._slis_available = None
        handler = mock.MagicMock()
        handler.get.return_value = mock.MagicMock(status_code=status_code)
        with mock.patch.object(check, "log") as log:
            check.detect_sli_endpoint(handler, "https://localhost:443/metrics/slis")
            assert log.debug.called is expect_logged


def test_detect_sli_endpoint_available_flag_matches_200_status_exactly(instance):
    # Kills the core/ReplaceComparisonOperator_Eq_* (NotEq/Lt/LtE/Gt/GtE) and NumberReplacer mutants at
    # sli_metrics.py:65 (`self._slis_available = r.status_code == 200`).
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    for status_code, expected in [(200, True), (199, False), (201, False)]:
        check._slis_available = None
        handler = mock.MagicMock()
        handler.get.return_value = mock.MagicMock(status_code=status_code)
        assert check.detect_sli_endpoint(handler, "https://localhost:443/metrics/slis") is expected


def test_sli_metrics_transformer_filters_by_healthz_type(aggregator, instance):
    # Kills the core/ZeroIterationForLoop mutant at sli_metrics.py:72 and the
    # core/ReplaceComparisonOperator_Eq_* / AddNot mutants at sli_metrics.py:74
    # (`if metric_type == "healthz":`), which would drop or wrongly keep non-healthz samples.
    check = KubeAPIServerMetricsCheck(CHECK_NAME, {}, [instance])
    scraper_config = check.instance['sli_scraper_config']
    non_interned_healthz = "".join(["h", "e", "a", "l", "t", "h", "z"])
    metric = FakeMetric(
        [
            Sample("kubernetes_healthcheck", {"name": "etcd", "type": "healthz"}, 1.0),
            Sample("kubernetes_healthcheck", {"name": "ping", "type": non_interned_healthz}, 1.0),
            Sample("kubernetes_healthcheck", {"name": "apple", "type": "apple"}, 1.0),
            Sample("kubernetes_healthcheck", {"name": "log", "type": "readyz"}, 1.0),
        ],
        name="kubernetes_healthcheck",
        metric_type="gauge",
    )
    check.sli_metrics_transformer(metric, scraper_config)
    aggregator.assert_metric_has_tag("kube_apiserver.slis.kubernetes_healthcheck", "sli_name:etcd")
    aggregator.assert_metric_has_tag("kube_apiserver.slis.kubernetes_healthcheck", "sli_name:ping")
    aggregator.assert_metric("kube_apiserver.slis.kubernetes_healthcheck", count=2)
