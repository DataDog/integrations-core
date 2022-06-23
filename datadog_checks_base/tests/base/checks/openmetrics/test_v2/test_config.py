# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.testing import requires_py3

from .utils import get_check

pytestmark = [requires_py3]


class TestPrometheusEndpoint:
    def test_not_string(self, dd_run_check):
        check = get_check({'openmetrics_endpoint': 9000})

        with pytest.raises(Exception, match='^The setting `openmetrics_endpoint` must be a string$'):
            dd_run_check(check, extract_message=True)

    def test_missing(self, dd_run_check):
        check = get_check({'openmetrics_endpoint': ''})

        with pytest.raises(Exception, match='^The setting `openmetrics_endpoint` is required$'):
            dd_run_check(check, extract_message=True)


class TestNamespace:
    def test_not_string(self, dd_run_check):
        check = get_check({'namespace': 9000})
        check.__NAMESPACE__ = ''

        with pytest.raises(Exception, match='^Setting `namespace` must be a string$'):
            dd_run_check(check, extract_message=True)

    def test_not_string_override(self, dd_run_check):
        check = get_check({'namespace': 'foo'})
        check.__NAMESPACE__ = 9000

        with pytest.raises(Exception, match='^Setting `namespace` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestRawMetricPrefix:
    def test_not_string(self, dd_run_check):
        check = get_check({'raw_metric_prefix': 9000})

        with pytest.raises(Exception, match='^Setting `raw_metric_prefix` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestHostnameLabel:
    def test_not_string(self, dd_run_check):
        check = get_check({'hostname_label': 9000})

        with pytest.raises(Exception, match='^Setting `hostname_label` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestHostnameFormat:
    def test_not_string(self, dd_run_check):
        check = get_check({'hostname_format': 9000})

        with pytest.raises(Exception, match='^Setting `hostname_format` must be a string$'):
            dd_run_check(check, extract_message=True)

    def test_no_placeholder(self, dd_run_check):
        check = get_check({'hostname_label': 'foo', 'hostname_format': 'bar'})

        with pytest.raises(
            Exception, match='^Setting `hostname_format` does not contain the placeholder `<HOSTNAME>`$'
        ):
            dd_run_check(check, extract_message=True)


class TestExcludeLabels:
    def test_not_array(self, dd_run_check):
        check = get_check({'exclude_labels': 9000})

        with pytest.raises(Exception, match='^Setting `exclude_labels` must be an array$'):
            dd_run_check(check, extract_message=True)

    def test_entry_invalid_type(self, dd_run_check):
        check = get_check({'exclude_labels': [9000]})

        with pytest.raises(Exception, match='^Entry #1 of setting `exclude_labels` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestIncludeLabels:
    def test_inc_not_array(self, dd_run_check):
        check = get_check({'include_labels': 9000})

        with pytest.raises(Exception, match='^Setting `include_labels` must be an array$'):
            dd_run_check(check, extract_message=True)

    def test_inc_entry_invalid_type(self, dd_run_check):
        check = get_check({'include_labels': [9000]})

        with pytest.raises(Exception, match='^Entry #1 of setting `include_labels` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestRenameLabels:
    def test_not_mapping(self, dd_run_check):
        check = get_check({'rename_labels': 9000})

        with pytest.raises(Exception, match='^Setting `rename_labels` must be a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_value_not_string(self, dd_run_check):
        check = get_check({'rename_labels': {'foo': 9000}})

        with pytest.raises(Exception, match='^Value for label `foo` of setting `rename_labels` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestExcludeMetrics:
    def test_not_array(self, dd_run_check):
        check = get_check({'exclude_metrics': 9000})

        with pytest.raises(Exception, match='^Setting `exclude_metrics` must be an array$'):
            dd_run_check(check, extract_message=True)

    def test_entry_invalid_type(self, dd_run_check):
        check = get_check({'exclude_metrics': [9000]})

        with pytest.raises(Exception, match='^Entry #1 of setting `exclude_metrics` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestExcludeMetricsByLabels:
    def test_not_mapping(self, dd_run_check):
        check = get_check({'exclude_metrics_by_labels': 9000})

        with pytest.raises(Exception, match='^Setting `exclude_metrics_by_labels` must be a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_value_not_string(self, dd_run_check):
        check = get_check({'exclude_metrics_by_labels': {'foo': [9000]}})

        with pytest.raises(
            Exception, match='^Value #1 for label `foo` of setting `exclude_metrics_by_labels` must be a string$'
        ):
            dd_run_check(check, extract_message=True)

    def test_invalid_type(self, dd_run_check):
        check = get_check({'exclude_metrics_by_labels': {'foo': 9000}})

        with pytest.raises(
            Exception, match='^Label `foo` of setting `exclude_metrics_by_labels` must be an array or set to `true`$'
        ):
            dd_run_check(check, extract_message=True)


class TestTags:
    def test_not_array(self, dd_run_check):
        check = get_check({'tags': 9000})

        with pytest.raises(Exception, match='^Setting `tags` must be an array$'):
            dd_run_check(check, extract_message=True)

    def test_entry_invalid_type(self, dd_run_check):
        check = get_check({'tags': [9000]})

        with pytest.raises(Exception, match='^Entry #1 of setting `tags` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestRawLineFilters:
    def test_not_array(self, dd_run_check):
        check = get_check({'raw_line_filters': 9000})

        with pytest.raises(Exception, match='^Setting `raw_line_filters` must be an array$'):
            dd_run_check(check, extract_message=True)

    def test_entry_invalid_type(self, dd_run_check):
        check = get_check({'raw_line_filters': [9000]})

        with pytest.raises(Exception, match='^Entry #1 of setting `raw_line_filters` must be a string$'):
            dd_run_check(check, extract_message=True)

    def test_invalid_pattern(self, dd_run_check):
        check = get_check({'raw_line_filters': ['\\1']})

        with pytest.raises(Exception, match='^invalid group reference'):
            dd_run_check(check, extract_message=True)


class TestMetrics:
    def test_not_array(self, dd_run_check):
        check = get_check({'metrics': 9000})

        with pytest.raises(Exception, match='^Setting `metrics` must be an array$'):
            dd_run_check(check, extract_message=True)

    def test_entry_invalid_type(self, dd_run_check):
        check = get_check({'metrics': [9000]})

        with pytest.raises(Exception, match='^Entry #1 of setting `metrics` must be a string or a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_mapped_value_not_string(self, dd_run_check):
        check = get_check({'metrics': [{'foo': 9000}]})

        with pytest.raises(
            Exception, match='^Value of entry `foo` of setting `metrics` must be a string or a mapping$'
        ):
            dd_run_check(check, extract_message=True)

    def test_config_name_not_string(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'name': 9000}}]})

        with pytest.raises(
            Exception, match='^Error compiling transformer for metric `foo`: field `name` must be a string$'
        ):
            dd_run_check(check, extract_message=True)

    def test_config_type_not_string(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 9000}}]})

        with pytest.raises(
            Exception, match='^Error compiling transformer for metric `foo`: field `type` must be a string$'
        ):
            dd_run_check(check, extract_message=True)

    def test_config_type_unknown(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'bar'}}]})

        with pytest.raises(Exception, match='^Error compiling transformer for metric `foo`: unknown type `bar`$'):
            dd_run_check(check, extract_message=True)


class TestExtraMetrics:
    def test_not_array(self, dd_run_check):
        check = get_check({'extra_metrics': 9000})

        with pytest.raises(Exception, match='^Setting `extra_metrics` must be an array$'):
            dd_run_check(check, extract_message=True)

    def test_entry_invalid_type(self, dd_run_check):
        check = get_check({'extra_metrics': [9000]})

        with pytest.raises(Exception, match='^Entry #1 of setting `extra_metrics` must be a string or a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_mapped_value_not_string(self, dd_run_check):
        check = get_check({'extra_metrics': [{'foo': 9000}]})

        with pytest.raises(
            Exception, match='^Value of entry `foo` of setting `extra_metrics` must be a string or a mapping$'
        ):
            dd_run_check(check, extract_message=True)


class TestTransformerCompilation:
    def test_temporal_percent_no_scale(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'temporal_percent'}}]})

        with pytest.raises(
            Exception, match='^Error compiling transformer for metric `foo`: the `scale` parameter is required$'
        ):
            dd_run_check(check, extract_message=True)

    def test_temporal_percent_unknown_scale(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'temporal_percent', 'scale': 'bar'}}]})

        with pytest.raises(
            Exception, match='^Error compiling transformer for metric `foo`: the `scale` parameter must be one of: '
        ):
            dd_run_check(check, extract_message=True)

    def test_temporal_percent_scale_not_int(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'temporal_percent', 'scale': 1.23}}]})

        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for metric `foo`: '
                'the `scale` parameter must be an integer representing parts of a second e.g. 1000 for millisecond$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_no_status_map(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'service_check'}}]})

        with pytest.raises(
            Exception, match='^Error compiling transformer for metric `foo`: the `status_map` parameter is required$'
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_not_dict(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'service_check', 'status_map': 5}}]})

        with pytest.raises(
            Exception,
            match='^Error compiling transformer for metric `foo`: the `status_map` parameter must be a mapping$',
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_empty(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'service_check', 'status_map': {}}}]})

        with pytest.raises(
            Exception,
            match='^Error compiling transformer for metric `foo`: the `status_map` parameter must not be empty$',
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_value_not_number(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'service_check', 'status_map': {True: 'OK'}}}]})

        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for metric `foo`: '
                'value `True` of parameter `status_map` does not represent an integer$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_status_not_string(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'service_check', 'status_map': {'9000': 0}}}]})

        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for metric `foo`: '
                'status `0` for value `9000` of parameter `status_map` is not a string$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_status_invalid(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'service_check', 'status_map': {'9000': '0k'}}}]})

        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for metric `foo`: '
                'invalid status `0k` for value `9000` of parameter `status_map`$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_metadata_label_not_string(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'metadata', 'label': 9000}}]})

        with pytest.raises(
            Exception, match='^Error compiling transformer for metric `foo`: the `label` parameter must be a string$'
        ):
            dd_run_check(check, extract_message=True)

    def test_metadata_no_label(self, dd_run_check):
        check = get_check({'metrics': [{'foo': {'type': 'metadata'}}]})

        with pytest.raises(
            Exception, match='^Error compiling transformer for metric `foo`: the `label` parameter is required$'
        ):
            dd_run_check(check, extract_message=True)


class TestShareLabels:
    def test_not_mapping(self, dd_run_check):
        check = get_check({'share_labels': 9000})

        with pytest.raises(Exception, match='^Setting `share_labels` must be a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_invalid_type(self, dd_run_check):
        check = get_check({'share_labels': {'foo': 9000}})

        with pytest.raises(
            Exception, match='^Metric `foo` of setting `share_labels` must be a mapping or set to `true`$'
        ):
            dd_run_check(check, extract_message=True)

    def test_values_not_array(self, dd_run_check):
        check = get_check({'share_labels': {'foo': {'values': 9000}}})

        with pytest.raises(
            Exception, match='^Option `values` for metric `foo` of setting `share_labels` must be an array$'
        ):
            dd_run_check(check, extract_message=True)

    def test_values_entry_not_integer(self, dd_run_check):
        check = get_check({'share_labels': {'foo': {'values': [1.0]}}})

        with pytest.raises(
            Exception,
            match=(
                '^Entry #1 of option `values` for metric `foo` of setting `share_labels` must represent an integer$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    @pytest.mark.parametrize('option', ['labels', 'match'])
    def test_option_not_array(self, dd_run_check, option):
        check = get_check({'share_labels': {'foo': {option: 9000}}})

        with pytest.raises(
            Exception, match='^Option `{}` for metric `foo` of setting `share_labels` must be an array$'.format(option)
        ):
            dd_run_check(check, extract_message=True)

    @pytest.mark.parametrize('option', ['labels', 'match'])
    def test_option_entry_not_string(self, dd_run_check, option):
        check = get_check({'share_labels': {'foo': {option: [9000]}}})

        with pytest.raises(
            Exception,
            match=(
                '^Entry #1 of option `{}` for metric `foo` of setting `share_labels` must be a string$'.format(option)
            ),
        ):
            dd_run_check(check, extract_message=True)


class TestUseLatestSpec:
    def test_strict_latest_spec(self, dd_run_check):
        check = get_check({'use_latest_spec': True})
        check.configure_scrapers()
        scraper = check.scrapers['test']
        assert scraper.http.options['headers']['Accept'] == 'application/openmetrics-text; version=0.0.1; charset=utf-8'

    def test_plain_text_spec(self, dd_run_check):
        check = get_check({'use_latest_spec': False})
        check.configure_scrapers()
        scraper = check.scrapers['test']
        assert scraper.http.options['headers']['Accept'] == 'text/plain'
