# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from ..utils import requires_py3
from .utils import get_check

pytestmark = [requires_py3, pytest.mark.openmetrics, pytest.mark.openmetrics_options]


class TestNamespace:
    def test(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'namespace': 'foo'})
        check.__NAMESPACE__ = ''
        dd_run_check(check)

        aggregator.assert_metric(
            'foo.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test']
        )

        aggregator.assert_all_metrics_covered()


class TestRawMetricPrefix:
    def test(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP foo_go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE foo_go_memstats_alloc_bytes gauge
            foo_go_memstats_alloc_bytes 6.396288e+06
            """
        )
        check = get_check({'metrics': ['go_memstats_alloc_bytes'], 'raw_metric_prefix': 'foo_'})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test']
        )

        aggregator.assert_all_metrics_covered()


class TestEnableHealthServiceCheck:
    def test_default(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'tags': ['foo:bar']})
        dd_run_check(check)

        aggregator.assert_service_check('test.openmetrics.health', ServiceCheck.OK, tags=['endpoint:test', 'foo:bar'])

    def test_failure(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes 6.396288e+06
            """,
            status_code=401,
        )
        check = get_check({'metrics': ['.+'], 'tags': ['foo:bar']})

        with pytest.raises(Exception):
            dd_run_check(check)

        aggregator.assert_service_check(
            'test.openmetrics.health', ServiceCheck.CRITICAL, tags=['endpoint:test', 'foo:bar']
        )

    def test_disable(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes 6.396288e+06
            """,
            status_code=401,
        )
        check = get_check({'metrics': ['.+'], 'enable_health_service_check': False})

        with pytest.raises(Exception):
            dd_run_check(check)

        assert not aggregator.service_check_names


class TestHostnameLabel:
    def test(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'hostname_label': 'foo'})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'foo:bar'],
            hostname='bar',
        )

        aggregator.assert_all_metrics_covered()


class TestHostnameFormat:
    def test(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'hostname_label': 'foo', 'hostname_format': 'region_<HOSTNAME>'})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'foo:bar'],
            hostname='region_bar',
        )

        aggregator.assert_all_metrics_covered()


class TestExcludeLabels:
    def test(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar",bar="baz"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'exclude_labels': ['foo']})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'bar:baz']
        )

        aggregator.assert_all_metrics_covered()


class TestRenameLabels:
    def test(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="baz"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'rename_labels': {'foo': 'bar'}})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'bar:baz']
        )

        aggregator.assert_all_metrics_covered()


class TestExcludeMetrics:
    def test(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{bar="foo"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{foo="bar"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'exclude_metrics': ['^go_memstats_(alloc|free)_bytes$']})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes', 901120, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'bar:foo']
        )

        aggregator.assert_all_metrics_covered()


class TestExcludeMetricsByLabels:
    def test_pattern(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bat"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{foo="bar"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{foo="baz"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'exclude_metrics_by_labels': {'foo': ['ba(t|z)']}})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes', 901120, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'foo:bar']
        )

        aggregator.assert_all_metrics_covered()

    def test_all(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bat"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{foo="bar"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{foo="baz"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'exclude_metrics_by_labels': {'foo': True}})
        dd_run_check(check)

        aggregator.assert_all_metrics_covered()


class TestRawLineFilters:
    def test(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{bar=""} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{foo="bar"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{foo=""} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'raw_line_filters': ['=""']})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes', 901120, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'foo:bar']
        )

        aggregator.assert_all_metrics_covered()


class TestMetrics:
    def test_unknown_type_override(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes untyped
            go_memstats_alloc_bytes 6.396288e+06
            """
        )
        check = get_check({'metrics': [{'.+': {'type': 'gauge'}}]})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test']
        )

        aggregator.assert_all_metrics_covered()


class TestShareLabels:
    def test_unconditional_labels_all(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{bar="foo"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{bar="baz"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'share_labels': {'go_memstats_alloc_bytes': True}})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'foo:bar']
        )
        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes',
            901120,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:foo', 'foo:bar'],
        )
        aggregator.assert_metric(
            'test.go_memstats_free_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:baz', 'foo:bar'],
        )

        aggregator.assert_all_metrics_covered()

    def test_unconditional_labels_subset(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar",baz="foo"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{bar="foo"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{bar="baz"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'share_labels': {'go_memstats_alloc_bytes': {'labels': ['baz']}}})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'foo:bar', 'baz:foo'],
        )
        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes',
            901120,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:foo', 'baz:foo'],
        )
        aggregator.assert_metric(
            'test.go_memstats_free_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:baz', 'baz:foo'],
        )

        aggregator.assert_all_metrics_covered()

    def test_match_with_unconditional_labels(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar",baz="foo",pod="test"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{bar="foo",baz="foo"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{bar="baz",baz="bar"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'share_labels': {'go_memstats_alloc_bytes': {'match': ['baz']}}})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'foo:bar', 'baz:foo', 'pod:test'],
        )
        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes',
            901120,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:foo', 'baz:foo', 'foo:bar', 'pod:test'],
        )
        aggregator.assert_metric(
            'test.go_memstats_free_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:baz', 'baz:bar'],
        )

        aggregator.assert_all_metrics_covered()

    def test_match_with_select_labels(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar",baz="foo",pod="test"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{bar="foo",baz="foo"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{bar="baz",baz="bar"} 6.396288e+06
            """
        )
        check = get_check(
            {'metrics': ['.+'], 'share_labels': {'go_memstats_alloc_bytes': {'match': ['baz'], 'labels': ['pod']}}}
        )
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'foo:bar', 'baz:foo', 'pod:test'],
        )
        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes',
            901120,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:foo', 'baz:foo', 'pod:test'],
        )
        aggregator.assert_metric(
            'test.go_memstats_free_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:baz', 'baz:bar'],
        )

        aggregator.assert_all_metrics_covered()

    @pytest.mark.parametrize('values', [pytest.param([6396288], id='integer'), pytest.param(['6396288'], id='string')])
    def test_values_match(self, aggregator, dd_run_check, mock_http_response, values):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{bar="foo"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{bar="baz"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'share_labels': {'go_memstats_alloc_bytes': {'values': values}}})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'foo:bar']
        )
        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes',
            901120,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:foo', 'foo:bar'],
        )
        aggregator.assert_metric(
            'test.go_memstats_free_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:baz', 'foo:bar'],
        )

        aggregator.assert_all_metrics_covered()

    def test_values_no_match(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{bar="foo"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{bar="baz"} 6.396288e+06
            """
        )
        check = get_check({'metrics': ['.+'], 'share_labels': {'go_memstats_alloc_bytes': {'values': [9000]}}})
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'foo:bar']
        )
        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes', 901120, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'bar:foo']
        )
        aggregator.assert_metric(
            'test.go_memstats_free_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'bar:baz']
        )

        aggregator.assert_all_metrics_covered()

    def test_excluded_metric(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar"} 6.396288e+06
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{bar="foo"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{bar="baz"} 6.396288e+06
            """
        )
        check = get_check(
            {
                'metrics': ['.+'],
                'share_labels': {'go_memstats_alloc_bytes': True},
                'exclude_metrics': ['go_memstats_alloc_bytes'],
            }
        )
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_gc_sys_bytes',
            901120,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:foo', 'foo:bar'],
        )
        aggregator.assert_metric(
            'test.go_memstats_free_bytes',
            6396288,
            metric_type=aggregator.GAUGE,
            tags=['endpoint:test', 'bar:baz', 'foo:bar'],
        )

        aggregator.assert_all_metrics_covered()
