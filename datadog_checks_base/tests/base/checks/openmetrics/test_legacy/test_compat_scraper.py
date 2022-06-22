# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.testing import requires_py3

from .utils import get_legacy_check

pytestmark = [requires_py3]


class TestRawMetricPrefix:
    def test_not_string(self, dd_run_check):
        check = get_legacy_check({'prometheus_metrics_prefix': 9000})

        with pytest.raises(Exception, match='^Setting `raw_metric_prefix` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestHostnameLabel:
    def test_not_string(self, dd_run_check):
        check = get_legacy_check({'label_to_hostname': 9000})

        with pytest.raises(Exception, match='^Setting `hostname_label` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestRenameLabels:
    def test_not_mapping(self, dd_run_check):
        check = get_legacy_check({'labels_mapper': 9000})

        with pytest.raises(Exception, match='^Setting `rename_labels` must be a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_value_not_string(self, dd_run_check):
        check = get_legacy_check({'labels_mapper': {'foo': 9000}})

        with pytest.raises(Exception, match='^Value for label `foo` of setting `rename_labels` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestExcludeMetrics:
    def test_entry_invalid_type(self, dd_run_check):
        check = get_legacy_check({'exclude_metrics': [9000]})

        with pytest.raises(Exception, match='^Entry #1 of setting `exclude_metrics` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestExcludeMetricsByLabels:
    def test_value_not_string(self, dd_run_check):
        check = get_legacy_check({'ignore_metrics_by_labels': {'foo': [9000]}})

        with pytest.raises(
            Exception, match='^Value #1 for label `foo` of setting `exclude_metrics_by_labels` must be a string$'
        ):
            dd_run_check(check, extract_message=True)


class TestShareLabels:
    def test_not_mapping(self, dd_run_check):
        check = get_legacy_check({'share_labels': 9000})

        with pytest.raises(Exception, match='^Setting `share_labels` must be a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_invalid_type(self, dd_run_check):
        check = get_legacy_check({'share_labels': {'foo': 9000}})

        with pytest.raises(
            Exception, match='^Metric `foo` of setting `share_labels` must be a mapping or set to `true`$'
        ):
            dd_run_check(check, extract_message=True)

    def test_values_not_array(self, dd_run_check):
        check = get_legacy_check({'share_labels': {'foo': {'values': 9000}}})

        with pytest.raises(
            Exception, match='^Option `values` for metric `foo` of setting `share_labels` must be an array$'
        ):
            dd_run_check(check, extract_message=True)

    def test_values_entry_not_integer(self, dd_run_check):
        check = get_legacy_check({'share_labels': {'foo': {'values': [1.0]}}})

        with pytest.raises(
            Exception,
            match=(
                '^Entry #1 of option `values` for metric `foo` of setting `share_labels` must represent an integer$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    @pytest.mark.parametrize('option', ['labels', 'match'])
    def test_option_not_array(self, dd_run_check, option):
        check = get_legacy_check({'share_labels': {'foo': {option: 9000}}})

        with pytest.raises(
            Exception, match='^Option `{}` for metric `foo` of setting `share_labels` must be an array$'.format(option)
        ):
            dd_run_check(check, extract_message=True)

    @pytest.mark.parametrize('option', ['labels', 'match'])
    def test_option_entry_not_string(self, dd_run_check, option):
        check = get_legacy_check({'share_labels': {'foo': {option: [9000]}}})

        with pytest.raises(
            Exception,
            match=(
                '^Entry #1 of option `{}` for metric `foo` of setting `share_labels` must be a string$'.format(option)
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_share_labels(self, aggregator, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
            # TYPE go_memstats_alloc_bytes gauge
            go_memstats_alloc_bytes{foo="bar",baz="foo",pod="test"} 1
            # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
            # TYPE go_memstats_gc_sys_bytes gauge
            go_memstats_gc_sys_bytes{bar="foo",baz="foo"} 901120
            # HELP go_memstats_free_bytes Number of bytes free and available for use.
            # TYPE go_memstats_free_bytes gauge
            go_memstats_free_bytes{bar="baz",baz="bar"} 6.396288e+06
            """
        )
        check = get_legacy_check(
            {
                'metrics': ['*'],
                'label_joins': {'go_memstats_alloc_bytes': {'labels_to_match': ['baz'], 'labels_to_get': ['pod']}},
            }
        )
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes',
            1,
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

    def test_metadata(self, aggregator, datadog_agent, dd_run_check, mock_http_response):
        mock_http_response(
            """
            # HELP kubernetes_build_info A metric with a constant '1' value labeled by major, minor, git version, git commit, git tree state, build date, Go version, and compiler from which Kubernetes was built, and platform on which it is running.
            # TYPE kubernetes_build_info gauge
            kubernetes_build_info{buildDate="2016-11-18T23:57:26Z",compiler="gc",gitCommit="3872cb93abf9482d770e651b5fe14667a6fca7e0",gitTreeState="dirty",gitVersion="v1.6.0-alpha.0.680+3872cb93abf948-dirty",goVersion="go1.7.3",major="1",minor="6+",platform="linux/amd64"} 1
            """  # noqa: E501
        )
        check = get_legacy_check(
            {'metadata_metric_name': 'kubernetes_build_info', 'metadata_label_map': {'version': 'gitVersion'}}
        )
        check.check_id = 'test:instance'
        dd_run_check(check)

        version_metadata = {
            'version.major': '1',
            'version.minor': '6',
            'version.patch': '0',
            'version.release': 'alpha.0.680',
            'version.build': '3872cb93abf948-dirty',
            'version.raw': 'v1.6.0-alpha.0.680+3872cb93abf948-dirty',
            'version.scheme': 'semver',
        }

        datadog_agent.assert_metadata('test:instance', version_metadata)
        datadog_agent.assert_metadata_count(len(version_metadata))
        aggregator.assert_all_metrics_covered()
