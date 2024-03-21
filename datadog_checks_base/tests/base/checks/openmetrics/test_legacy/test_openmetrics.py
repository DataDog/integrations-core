# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2016-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import io
import logging
import math
import os
import re
import time

import mock
import pytest
import requests
from mock import patch
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, HistogramMetricFamily, SummaryMetricFamily
from prometheus_client.samples import Sample
from six import iteritems

from datadog_checks.base import ensure_bytes
from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.dev import get_here
from datadog_checks.dev.http import MockResponse

text_content_type = 'text/plain; version=0.0.4'
FIXTURE_PATH = os.path.abspath(os.path.join(get_here(), '..', '..', '..', '..', 'fixtures', 'prometheus'))
TOKENS_PATH = os.path.abspath(os.path.join(get_here(), '..', '..', '..', '..', 'fixtures', 'bearer_tokens'))

FAKE_ENDPOINT = 'http://fake.endpoint:10055/metrics'

PROMETHEUS_CHECK_INSTANCE = {
    'prometheus_url': FAKE_ENDPOINT,
    'metrics': [{'process_virtual_memory_bytes': 'process.vm.bytes'}],
    'namespace': 'prometheus',
    # Defaults for checks that were based on PrometheusCheck
    'send_monotonic_counter': False,
    'health_service_check': True,
}

OPENMETRICS_CHECK_INSTANCE = {
    'prometheus_url': 'http://fake.endpoint:10055/metrics',
    'metrics': [{'process_virtual_memory_bytes': 'process.vm.bytes'}],
    'namespace': 'openmetrics',
}


@pytest.fixture
def mocked_prometheus_check():
    check = OpenMetricsBaseCheck('prometheus_check', {}, {})
    check.log = logging.getLogger('datadog-prometheus.test')
    check.log.debug = mock.MagicMock()
    return check


@pytest.fixture
def mocked_openmetrics_check_factory():
    def factory(instance):
        check = OpenMetricsBaseCheck('openmetrics_check', {}, [instance])
        check.check_id = 'test:123'
        check.log = logging.getLogger('datadog-openmetrics.test')
        check.log.debug = mock.MagicMock()
        return check

    return factory


@pytest.fixture
def mocked_prometheus_scraper_config(mocked_prometheus_check):
    yield mocked_prometheus_check.get_scraper_config(PROMETHEUS_CHECK_INSTANCE)


@pytest.fixture
def p_check():
    return OpenMetricsBaseCheck('prometheus_check', {}, {})


@pytest.fixture
def ref_gauge():
    ref_gauge = GaugeMetricFamily('process_virtual_memory_bytes', 'Virtual memory size in bytes.')
    ref_gauge.add_metric([], 54927360.0)

    return ref_gauge


@pytest.fixture
def text_data():
    # Loading test text data
    f_name = os.path.join(FIXTURE_PATH, 'metrics.txt')
    with open(f_name, 'r') as f:
        data = f.read()
        assert len(data) == 14494

    yield data


@pytest.fixture
def mock_get(mock_http_response):
    yield mock_http_response(
        file_path=os.path.join(FIXTURE_PATH, 'ksm.txt'), headers={'Content-Type': text_content_type}
    ).return_value.text


def test_config_instance(mocked_prometheus_check):
    """Ensure scraper config persists instance options"""
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    instance['new_option'] = 'test123'

    config = check.create_scraper_configuration(instance)
    config['new_option'] = 'test123'


def test_process(text_data, mocked_prometheus_check, mocked_prometheus_scraper_config, ref_gauge):
    check = mocked_prometheus_check
    check.poll = mock.MagicMock(return_value=MockResponse(text_data, headers={'Content-Type': text_content_type}))
    check.process_metric = mock.MagicMock()
    check.process(mocked_prometheus_scraper_config)
    check.poll.assert_called_with(mocked_prometheus_scraper_config)
    check.process_metric.assert_called_with(
        ref_gauge,
        mocked_prometheus_scraper_config,
        metric_transformers=mocked_prometheus_scraper_config['_default_metric_transformers'],
    )


def test_process_metric_gauge(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, ref_gauge):
    """Gauge ref submission"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['_dry_run'] = False
    check.process_metric(ref_gauge, mocked_prometheus_scraper_config)

    aggregator.assert_metric('prometheus.process.vm.bytes', 54927360.0, tags=[], count=1)


def test_process_metric_filtered(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """Metric absent from the metrics_mapper"""
    filtered_gauge = GaugeMetricFamily(
        'process_start_time_seconds', 'Start time of the process since unix epoch in seconds.'
    )
    filtered_gauge.add_metric([], 123456789.0)
    mocked_prometheus_scraper_config['_dry_run'] = False

    check = mocked_prometheus_check
    check.process_metric(filtered_gauge, mocked_prometheus_scraper_config, metric_transformers={})
    check.log.debug.assert_called_with(
        'Skipping metric `%s` as it is not defined in the metrics mapper, '
        'has no transformer function, nor does it match any wildcards.',
        'process_start_time_seconds',
    )
    aggregator.assert_all_metrics_covered()


def test_poll_text_plain(mocked_prometheus_check, mocked_prometheus_scraper_config, text_data):
    """Tests poll using the text format"""
    check = mocked_prometheus_check
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': text_content_type}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        response = check.poll(mocked_prometheus_scraper_config)
        messages = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))
        messages.sort(key=lambda x: x.name)
        assert len(messages) == 40
        assert messages[-1].name == 'skydns_skydns_dns_response_size_bytes'


def test_poll_octet_stream(mocked_prometheus_check, mocked_prometheus_scraper_config, text_data):
    """Tests poll using the text format"""
    check = mocked_prometheus_check

    mock_response = requests.Response()
    mock_response.raw = io.BytesIO(ensure_bytes(text_data))
    mock_response.status_code = 200
    mock_response.headers = {'Content-Type': 'application/octet-stream'}

    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        response = check.poll(mocked_prometheus_scraper_config)
        messages = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))
        assert len(messages) == 40


def test_submit_gauge_with_labels(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """submitting metrics that contain labels should result in tags on the gauge call"""
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes',
        'Virtual memory size in bytes.',
        labels=['my_1st_label', 'my_2nd_label', 'labél_nat', 'labél_mix', u'labél_uni'],
    )
    ref_gauge.add_metric(
        ['my_1st_label_value', 'my_2nd_label_value', 'my_labél_val', u'my_labél_val🐶', u'my_labél_val'], 54927360.0
    )

    check = mocked_prometheus_check
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric_name, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=[
            'my_1st_label:my_1st_label_value',
            'my_2nd_label:my_2nd_label_value',
            'labél_nat:my_labél_val',
            'labél_mix:my_labél_val🐶',
            'labél_uni:my_labél_val',
        ],
        count=1,
    )


def test_submit_gauge_with_labels_and_hostname_override(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config
):
    """submitting metrics that contain labels should result in tags on the gauge call"""
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'node']
    )
    ref_gauge.add_metric(['my_1st_label_value', 'foo'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['label_to_hostname'] = 'node'
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric_name, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['my_1st_label:my_1st_label_value', 'node:foo'],
        hostname="foo",
        count=1,
    )

    # also test with a hostname suffix
    check2 = mocked_prometheus_check
    mocked_prometheus_scraper_config['label_to_hostname'] = 'node'
    mocked_prometheus_scraper_config['label_to_hostname_suffix'] = '-cluster-blue'
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check2.submit_openmetric(metric_name, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['my_1st_label:my_1st_label_value', 'node:foo'],
        hostname="foo-cluster-blue",
        count=1,
    )


def test_submit_gauge_with_labels_and_hostname_override_empty_label(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config
):
    """submitting metrics that contain empty label_to_hostname"""
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'node']
    )
    ref_gauge.add_metric(['my_1st_label_value', ''], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['label_to_hostname'] = 'node'
    mocked_prometheus_scraper_config['label_to_hostname_suffix'] = '-cluster-name'
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric_name, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['my_1st_label:my_1st_label_value', 'node:'],
        hostname="",
        count=1,
    )


def test_submit_gauge_with_labels_and_hostname_already_overridden(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config
):
    """submitting metrics that contain labels should result in tags on the gauge call"""
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'node']
    )
    ref_gauge.add_metric(['my_1st_label_value', 'foo'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['label_to_hostname'] = 'node'
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric_name, ref_gauge, mocked_prometheus_scraper_config, hostname='bar')
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['my_1st_label:my_1st_label_value', 'node:foo'],
        hostname="bar",
        count=1,
    )


def test_labels_not_added_as_tag_once_for_each_metric(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, ref_gauge
):
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'my_2nd_label']
    )
    ref_gauge.add_metric(['my_1st_label_value', 'my_2nd_label_value'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['custom_tags'] = ['test']
    metric = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric, ref_gauge, mocked_prometheus_scraper_config)
    # Call a second time to check that the labels were not added once more to the tags list and
    # avoid regression on https://github.com/DataDog/dd-agent/pull/3359
    check.submit_openmetric(metric, ref_gauge, mocked_prometheus_scraper_config)

    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['test', 'my_1st_label:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'],
        count=2,
    )


def test_submit_gauge_with_custom_tags(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, ref_gauge
):
    """Providing custom tags should add them as is on the gauge call"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['custom_tags'] = ['env:dev', 'app:my_pretty_app']
    mocked_prometheus_scraper_config['_metric_tags'] = ['foo:bar']
    metric = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=mocked_prometheus_scraper_config['custom_tags'] + mocked_prometheus_scraper_config['_metric_tags'],
        count=1,
    )


def test_submit_gauge_with_labels_mapper(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """
    Submitting metrics that contain labels mappers should result in tags
    on the gauge call with transformed tag names
    """
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'my_2nd_label']
    )
    ref_gauge.add_metric(['my_1st_label_value', 'my_2nd_label_value'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['labels_mapper'] = {
        'my_1st_label': 'transformed_1st',
        'non_existent': 'should_not_matter',
        'env': 'dont_touch_custom_tags',
    }
    mocked_prometheus_scraper_config['custom_tags'] = ['env:dev', 'app:my_pretty_app']
    metric = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['env:dev', 'app:my_pretty_app', 'transformed_1st:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'],
        count=1,
    )


@pytest.mark.parametrize(
    'excluded_labels, included_labels, expected',
    (
        (
            ['my_2nd_label', 'whatever_else', 'env'],
            [],
            ['env:dev', 'app:my_pretty_app', 'transformed_1st_label:my_1st_label_value'],
        ),
        (
            [],
            ['my_2nd_label', 'whatever_else', 'env'],
            ['env:dev', 'app:my_pretty_app', 'my_2nd_label:my_2nd_label_value'],
        ),
        (
            ['my_2nd_label', 'whatever_else', 'env'],
            ['my_1st_label', 'whatever_else', 'env'],
            ['env:dev', 'app:my_pretty_app', 'transformed_1st_label:my_1st_label_value'],
        ),
        (
            ['my_2nd_label', 'whatever_else', 'env'],
            ['my_1st_label', 'my_2nd_label', 'whatever_else', 'env'],
            ['env:dev', 'app:my_pretty_app', 'transformed_1st_label:my_1st_label_value'],
        ),
    ),
    ids=(
        'Test excluded labels.',
        'Test included labels.',
        'Test both excluded and included labels, no override.',
        'Test both excluded and included labels with override.',
    ),
)
def test_submit_gauge_with_exclude_include_labels(
    aggregator,
    mocked_prometheus_check,
    mocked_prometheus_scraper_config,
    excluded_labels,
    included_labels,
    expected,
):
    """
    Submitting metrics when filtering with exclude_labels and/or include_labels should
    end up with a filtered tags list, where exclude_labels are excluded and
    include_labels are included. Labels that are present in both exclude_labels and include_labels are excluded.
    """
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'my_2nd_label']
    )
    ref_gauge.add_metric(['my_1st_label_value', 'my_2nd_label_value'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['labels_mapper'] = {
        'my_1st_label': 'transformed_1st_label',
        'non_existent': 'should_not_matter',
        'env': 'dont_touch_custom_tags',
    }
    mocked_prometheus_scraper_config['custom_tags'] = ['env:dev', 'app:my_pretty_app']
    mocked_prometheus_scraper_config['exclude_labels'] = excluded_labels
    mocked_prometheus_scraper_config['include_labels'] = included_labels
    metric = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=expected,
        count=1,
    )


@pytest.mark.parametrize(
    'config, counter_metric_monotonic, counter_with_gauge',
    (
        ({'send_monotonic_counter': True}, True, False),
        ({'send_monotonic_counter': False}, False, False),
        ({'send_monotonic_counter': False, 'send_monotonic_with_gauge': True}, False, True),
        ({'send_monotonic_counter': True, 'send_monotonic_with_gauge': True}, True, False),
    ),
    ids=(
        'default',
        'override default send_monotonic_counter',
        'send monotonic_counter with gauge',
        'ignore send_monotonic_with_gauge flag',
    ),
)
def test_submit_counter(
    aggregator,
    mocked_prometheus_check,
    mocked_prometheus_scraper_config,
    config,
    counter_metric_monotonic,
    counter_with_gauge,
):
    # Determine expected metric types for counter metrics
    counter_type = aggregator.GAUGE
    if counter_metric_monotonic:
        counter_type = aggregator.MONOTONIC_COUNT

    metric_name = 'prometheus.custom.counter'
    _counter = CounterMetricFamily('my_counter', 'Random counter')
    _counter.add_metric([], 42)
    mocked_prometheus_scraper_config.update(config)
    check = mocked_prometheus_check
    check.submit_openmetric('custom.counter', _counter, mocked_prometheus_scraper_config)
    aggregator.assert_metric(metric_name, 42, tags=[], count=1, metric_type=counter_type)

    if counter_with_gauge:
        aggregator.assert_metric(metric_name + '.total', 42, tags=[], count=1, metric_type=aggregator.MONOTONIC_COUNT)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    'config, count_metric_monotonic, sum_metric_monotonic, count_monotonic_gauge, sum_monotonic_gauge',
    (
        ({}, False, False, False, False),
        ({'send_distribution_counts_as_monotonic': True}, True, False, False, False),
        ({'send_distribution_sums_as_monotonic': True}, False, True, False, False),
        (
            {'send_distribution_counts_as_monotonic': True, 'send_distribution_sums_as_monotonic': True},
            True,
            True,
            False,
            False,
        ),
        ({'send_monotonic_with_gauge': True}, False, False, True, True),
        ({'send_monotonic_with_gauge': True, 'send_distribution_counts_as_monotonic': True}, True, False, False, True),
        ({'send_monotonic_with_gauge': True, 'send_distribution_sums_as_monotonic': True}, False, True, True, False),
        (
            {
                'send_monotonic_with_gauge': True,
                'send_distribution_sums_as_monotonic': True,
                'send_distribution_counts_as_monotonic': True,
            },
            True,
            True,
            False,
            False,
        ),
    ),
    ids=(
        'default',
        'count only as monotonic_count',
        'sum only as monotonic_count',
        'count and sum as monotonic_count',
        'count and sum with monotonic and gauge',
        'count only with monotonic_count and gauge',
        'sum only with monotonic_count and gauge',
        'ignore send_montonic_with_gauge flag',
    ),
)
def test_submit_summary(
    aggregator,
    mocked_prometheus_check,
    mocked_prometheus_scraper_config,
    config,
    count_metric_monotonic,
    sum_metric_monotonic,
    count_monotonic_gauge,
    sum_monotonic_gauge,
):
    # Determine expected metric types for `.count` and `.sum` metrics
    count_type = aggregator.GAUGE
    sum_type = aggregator.GAUGE

    if count_metric_monotonic:
        count_type = aggregator.MONOTONIC_COUNT
    if sum_metric_monotonic:
        sum_type = aggregator.MONOTONIC_COUNT

    mocked_prometheus_scraper_config.update(config)

    _sum = SummaryMetricFamily('my_summary', 'Random summary')
    _sum.add_metric([], 5.0, 120512.0)
    _sum.add_sample("my_summary", {"quantile": "0.5"}, 24547.0)
    _sum.add_sample("my_summary", {"quantile": "0.9"}, 25763.0)
    _sum.add_sample("my_summary", {"quantile": "0.99"}, 25763.0)
    _sum.add_sample("my_summary", {}, 25764.0)  # Quantile-less not supported yet and should be skipped.
    check = mocked_prometheus_check
    check.submit_openmetric('custom.summary', _sum, mocked_prometheus_scraper_config)

    aggregator.assert_metric('prometheus.custom.summary.count', 5.0, tags=[], count=1, metric_type=count_type)
    aggregator.assert_metric('prometheus.custom.summary.sum', 120512.0, tags=[], count=1, metric_type=sum_type)

    aggregator.assert_metric('prometheus.custom.summary.quantile', 24547.0, tags=['quantile:0.5'], count=1)
    aggregator.assert_metric('prometheus.custom.summary.quantile', 25763.0, tags=['quantile:0.9'], count=1)
    aggregator.assert_metric('prometheus.custom.summary.quantile', 25763.0, tags=['quantile:0.99'], count=1)
    aggregator.assert_metric('prometheus.custom.summary.quantile', 25764.0, tags=[], count=0)

    # If `send_monotonic_with_gauge` is true, assert a monotonic_count with suffixed `.total` is submitted
    if count_monotonic_gauge:
        aggregator.assert_metric(
            'prometheus.custom.summary.count.total', 5.0, tags=[], count=1, metric_type=aggregator.MONOTONIC_COUNT
        )

    if sum_monotonic_gauge:
        aggregator.assert_metric(
            'prometheus.custom.summary.sum.total', 120512.0, tags=[], count=1, metric_type=aggregator.MONOTONIC_COUNT
        )

    aggregator.assert_all_metrics_covered()


def assert_histogram_counts(aggregator, count_type, suffix=False):
    # Refactor commonly used metric assertion for the `test_submit_histogram` tests
    metric_name = 'prometheus.custom.histogram.count'
    # Append `.total` to monotonic_count metrics submitted with gauge
    if suffix:
        metric_name += '.total'

    aggregator.assert_metric(metric_name, 4, tags=['upper_bound:none'], count=1, metric_type=count_type)
    aggregator.assert_metric(metric_name, 1, tags=['upper_bound:1.0'], count=1, metric_type=count_type)
    aggregator.assert_metric(metric_name, 2, tags=['upper_bound:31104000.0'], count=1, metric_type=count_type)
    aggregator.assert_metric(metric_name, 3, tags=['upper_bound:432400000.0'], count=1, metric_type=count_type)


@pytest.mark.parametrize(
    'config, count_metric_monotonic, sum_metric_monotonic, count_monotonic_gauge, sum_monotonic_gauge',
    (
        ({}, False, False, False, False),
        ({'send_distribution_counts_as_monotonic': True}, True, False, False, False),
        ({'send_distribution_sums_as_monotonic': True}, False, True, False, False),
        (
            {'send_distribution_counts_as_monotonic': True, 'send_distribution_sums_as_monotonic': True},
            True,
            True,
            False,
            False,
        ),
        ({'send_monotonic_with_gauge': True}, False, False, True, True),
        ({'send_monotonic_with_gauge': True, 'send_distribution_counts_as_monotonic': True}, True, False, False, True),
        ({'send_monotonic_with_gauge': True, 'send_distribution_sums_as_monotonic': True}, False, True, True, False),
        (
            {
                'send_monotonic_with_gauge': True,
                'send_distribution_sums_as_monotonic': True,
                'send_distribution_counts_as_monotonic': True,
            },
            True,
            True,
            False,
            False,
        ),
    ),
    ids=(
        'default',
        'count only as monotonic_count',
        'sum only as monotonic_count',
        'count and sum as monotonic_count',
        'count and sum with monotonic and gauge',
        'count only with monotonic_count and gauge',
        'sum only with monotonic_count and gauge',
        'ignore send_montonic_with_gauge flag',
    ),
)
def test_submit_histograms(
    aggregator,
    mocked_prometheus_check,
    mocked_prometheus_scraper_config,
    config,
    count_metric_monotonic,
    sum_metric_monotonic,
    count_monotonic_gauge,
    sum_monotonic_gauge,
):
    # Determine expected metric types for `.count` and `.sum` metrics
    count_type = aggregator.GAUGE
    sum_type = aggregator.GAUGE
    if count_metric_monotonic:
        count_type = aggregator.MONOTONIC_COUNT
    if sum_metric_monotonic:
        sum_type = aggregator.MONOTONIC_COUNT

    _histo = HistogramMetricFamily('my_histogram', 'my_histogram')
    _histo.add_metric([], buckets=[("1", 1), ("3.1104e+07", 2), ("4.324e+08", 3), ("+Inf", 4)], sum_value=1337)
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config.update(config)

    check.submit_openmetric('custom.histogram', _histo, mocked_prometheus_scraper_config)
    aggregator.assert_metric('prometheus.custom.histogram.sum', 1337, tags=[], count=1, metric_type=sum_type)
    assert_histogram_counts(aggregator, count_type)

    # If `send_monotonic_with_gauge` is true, assert a monotonic_count with suffixed `.total` is submitted
    if count_monotonic_gauge:
        assert_histogram_counts(aggregator, aggregator.MONOTONIC_COUNT, True)

    if sum_monotonic_gauge:
        aggregator.assert_metric(
            'prometheus.custom.histogram.sum.total', 1337, tags=[], count=1, metric_type=aggregator.MONOTONIC_COUNT
        )

    aggregator.assert_all_metrics_covered()


def test_submit_buckets_as_distribution(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    _histo = HistogramMetricFamily('my_histogram', 'my_histogram')
    _histo.add_metric([], buckets=[("1", 1), ("3.1104e+07", 2), ("4.324e+08", 3), ("+Inf", 4)], sum_value=1337)
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['send_distribution_buckets'] = True
    mocked_prometheus_scraper_config['non_cumulative_buckets'] = True
    check.submit_openmetric('custom.histogram', _histo, mocked_prometheus_scraper_config)
    # sum & count gauges should not be sent
    aggregator.assert_metric('prometheus.custom.histogram.sum', 1337, tags=[], count=0)
    aggregator.assert_metric('prometheus.custom.histogram.count', 4, tags=['upper_bound:none'], count=0)
    # assert buckets
    aggregator.assert_histogram_bucket(
        'prometheus.custom.histogram',
        1,
        0.0,
        1.0,
        True,
        "",
        tags=['lower_bound:0.0', 'upper_bound:1.0'],
        count=None,
        at_least=1,
    )
    aggregator.assert_histogram_bucket(
        'prometheus.custom.histogram',
        1,
        1.0,
        31104000.0,
        True,
        "",
        tags=['lower_bound:1.0', 'upper_bound:31104000.0'],
        count=None,
        at_least=1,
    )
    aggregator.assert_histogram_bucket(
        'prometheus.custom.histogram',
        1,
        31104000.0,
        432400000.0,
        True,
        "",
        tags=['lower_bound:31104000.0', 'upper_bound:432400000.0'],
        count=None,
        at_least=1,
    )
    aggregator.assert_histogram_bucket(
        'prometheus.custom.histogram',
        1,
        432400000.0,
        float('inf'),
        True,
        "",
        tags=['lower_bound:432400000.0', 'upper_bound:inf'],
        count=None,
        at_least=1,
    )


def test_submit_rate(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    _rate = GaugeMetricFamily('my_rate', 'Random rate')
    _rate.add_metric([], 42)
    check = mocked_prometheus_check
    check.submit_openmetric('custom.rate', _rate, mocked_prometheus_scraper_config)
    aggregator.assert_metric('prometheus.custom.rate', 42, tags=[], count=1)


def test_filter_sample_on_gauge(p_check, mocked_prometheus_scraper_config):
    """
    Add a filter blacklist on the check matching one line and make sure
    only the two other lines are parsed and sent downstream.
    """
    text_data = (
        '# HELP kube_deployment_status_replicas The number of replicas per deployment.\n'
        '# TYPE kube_deployment_status_replicas gauge\n'
        'kube_deployment_status_replicas{deployment="event-exporter-v0.1.7"} 1\n'
        'kube_deployment_status_replicas{deployment="heapster-v1.4.3"} 1\n'
        'kube_deployment_status_replicas{deployment="kube-dns"} 2\n'
    )

    expected_metric = GaugeMetricFamily(
        'kube_deployment_status_replicas', 'The number of replicas per deployment.', labels=['deployment']
    )
    expected_metric.add_metric(['event-exporter-v0.1.7'], 1)
    expected_metric.add_metric(['heapster-v1.4.3'], 1)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    mocked_prometheus_scraper_config['_text_filter_blacklist'] = ["deployment=\"kube-dns\""]
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_metric == current_metric


def test_parse_one_gauge(p_check, mocked_prometheus_scraper_config):
    """
    name: "etcd_server_has_leader"
    help: "Whether or not a leader exists. 1 is existence, 0 is not."
    type: GAUGE
    metric {
      gauge {
        value: 1.0
      }
    }
    """
    text_data = (
        "# HELP etcd_server_has_leader Whether or not a leader exists. 1 is existence, 0 is not.\n"
        "# TYPE etcd_server_has_leader gauge\n"
        "etcd_server_has_leader 1\n"
    )

    expected_etcd_metric = GaugeMetricFamily(
        'etcd_server_has_leader', 'Whether or not a leader exists. 1 is existence, 0 is not.'
    )
    expected_etcd_metric.add_metric([], 1)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric == current_metric


def test_parse_one_counter(p_check, mocked_prometheus_scraper_config):
    """
    name: "go_memstats_mallocs_total"
    help: "Total number of mallocs."
    type: COUNTER
    metric {
      counter {
        value: 18713.0
      }
    }
    """
    text_data = (
        "# HELP go_memstats_mallocs_total Total number of mallocs.\n"
        "# TYPE go_memstats_mallocs_total counter\n"
        "go_memstats_mallocs_total 18713\n"
    )

    expected_etcd_metric = CounterMetricFamily('go_memstats_mallocs_total', 'Total number of mallocs.')
    expected_etcd_metric.add_metric([], 18713)
    # Fix up the _total change
    expected_etcd_metric.name = 'go_memstats_mallocs_total'

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric == current_metric


def test_parse_one_histograms_with_label(p_check, mocked_prometheus_scraper_config):
    text_data = (
        '# HELP etcd_disk_wal_fsync_duration_seconds The latency distributions of fsync called by wal.\n'
        '# TYPE etcd_disk_wal_fsync_duration_seconds histogram\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.001"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.002"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.004"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.008"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.016"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.032"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.064"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.128"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.256"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="0.512"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="1.024"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="2.048"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="4.096"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="8.192"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{app="vault",le="+Inf"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_sum{app="vault"} 0.026131671\n'
        'etcd_disk_wal_fsync_duration_seconds_count{app="vault"} 4\n'
    )

    expected_etcd_vault_metric = HistogramMetricFamily(
        'etcd_disk_wal_fsync_duration_seconds', 'The latency distributions of fsync called by wal.', labels=['app']
    )
    expected_etcd_vault_metric.add_metric(
        ['vault'],
        buckets=[
            ('0.001', 2.0),
            ('0.002', 2.0),
            ('0.004', 2.0),
            ('0.008', 2.0),
            ('0.016', 4.0),
            ('0.032', 4.0),
            ('0.064', 4.0),
            ('0.128', 4.0),
            ('0.256', 4.0),
            ('0.512', 4.0),
            ('1.024', 4.0),
            ('2.048', 4.0),
            ('4.096', 4.0),
            ('8.192', 4.0),
            ('+Inf', 4.0),
        ],
        sum_value=0.026131671,
    )

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_vault_metric.documentation == current_metric.documentation
    assert expected_etcd_vault_metric.name == current_metric.name
    assert expected_etcd_vault_metric.type == current_metric.type
    assert sorted(expected_etcd_vault_metric.samples, key=lambda i: i[0]) == sorted(
        current_metric.samples, key=lambda i: i[0]
    )


def test_parse_one_histogram(p_check, mocked_prometheus_scraper_config):
    """
    name: "etcd_disk_wal_fsync_duration_seconds"
    help: "The latency distributions of fsync called by wal."
    type: HISTOGRAM
    metric {
      histogram {
        sample_count: 4
        sample_sum: 0.026131671
        bucket {
          cumulative_count: 2
          upper_bound: 0.001
        }
        bucket {
          cumulative_count: 2
          upper_bound: 0.002
        }
        bucket {
          cumulative_count: 2
          upper_bound: 0.004
        }
        bucket {
          cumulative_count: 2
          upper_bound: 0.008
        }
        bucket {
          cumulative_count: 4
          upper_bound: 0.016
        }
        bucket {
          cumulative_count: 4
          upper_bound: 0.032
        }
        bucket {
          cumulative_count: 4
          upper_bound: 0.064
        }
        bucket {
          cumulative_count: 4
          upper_bound: 0.128
        }
        bucket {
          cumulative_count: 4
          upper_bound: 0.256
        }
        bucket {
          cumulative_count: 4
          upper_bound: 0.512
        }
        bucket {
          cumulative_count: 4
          upper_bound: 1.024
        }
        bucket {
          cumulative_count: 4
          upper_bound: 2.048
        }
        bucket {
          cumulative_count: 4
          upper_bound: 4.096
        }
        bucket {
          cumulative_count: 4
          upper_bound: 8.192
        }
        bucket {
          cumulative_count: 4
          upper_bound: inf
        }
      }
    }
    """
    text_data = (
        '# HELP etcd_disk_wal_fsync_duration_seconds The latency distributions of fsync called by wal.\n'
        '# TYPE etcd_disk_wal_fsync_duration_seconds histogram\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.001"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.002"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.004"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.008"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.016"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.032"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.064"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.128"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.256"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.512"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="1.024"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="2.048"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="4.096"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="8.192"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{le="+Inf"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_sum 0.026131671\n'
        'etcd_disk_wal_fsync_duration_seconds_count 4\n'
    )

    expected_etcd_metric = HistogramMetricFamily(
        'etcd_disk_wal_fsync_duration_seconds', 'The latency distributions of fsync called by wal.'
    )
    expected_etcd_metric.add_metric(
        [],
        buckets=[
            ('0.001', 2.0),
            ('0.002', 2.0),
            ('0.004', 2.0),
            ('0.008', 2.0),
            ('0.016', 4.0),
            ('0.032', 4.0),
            ('0.064', 4.0),
            ('0.128', 4.0),
            ('0.256', 4.0),
            ('0.512', 4.0),
            ('1.024', 4.0),
            ('2.048', 4.0),
            ('4.096', 4.0),
            ('8.192', 4.0),
            ('+Inf', 4.0),
        ],
        sum_value=0.026131671,
    )

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))
    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(
        current_metric.samples, key=lambda i: i[0]
    )


def test_parse_two_histograms_with_label(p_check, mocked_prometheus_scraper_config):
    text_data = (
        '# HELP etcd_disk_wal_fsync_duration_seconds The latency distributions of fsync called by wal.\n'
        '# TYPE etcd_disk_wal_fsync_duration_seconds histogram\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.001"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.002"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.004"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.008"} 2\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.016"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.032"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.064"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.128"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.256"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.512"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="1.024"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="2.048"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="4.096"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="8.192"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="+Inf"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_sum{kind="fs",app="vault"} 0.026131671\n'
        'etcd_disk_wal_fsync_duration_seconds_count{kind="fs",app="vault"} 4\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.001"} 718\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.002"} 740\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.004"} 743\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.008"} 748\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.016"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.032"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.064"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.128"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.256"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.512"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="1.024"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="2.048"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="4.096"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="8.192"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="+Inf"} 751\n'
        'etcd_disk_wal_fsync_duration_seconds_sum{kind="fs",app="kubernetes"} 0.3097010759999998\n'
        'etcd_disk_wal_fsync_duration_seconds_count{kind="fs",app="kubernetes"} 751\n'
    )

    expected_etcd_metric = HistogramMetricFamily(
        'etcd_disk_wal_fsync_duration_seconds',
        'The latency distributions of fsync called by wal.',
        labels=['kind', 'app'],
    )
    expected_etcd_metric.add_metric(
        ['fs', 'vault'],
        buckets=[
            ('0.001', 2.0),
            ('0.002', 2.0),
            ('0.004', 2.0),
            ('0.008', 2.0),
            ('0.016', 4.0),
            ('0.032', 4.0),
            ('0.064', 4.0),
            ('0.128', 4.0),
            ('0.256', 4.0),
            ('0.512', 4.0),
            ('1.024', 4.0),
            ('2.048', 4.0),
            ('4.096', 4.0),
            ('8.192', 4.0),
            ('+Inf', 4.0),
        ],
        sum_value=0.026131671,
    )
    expected_etcd_metric.add_metric(
        ['fs', 'kubernetes'],
        buckets=[
            ('0.001', 718.0),
            ('0.002', 740.0),
            ('0.004', 743.0),
            ('0.008', 748.0),
            ('0.016', 751.0),
            ('0.032', 751.0),
            ('0.064', 751.0),
            ('0.128', 751.0),
            ('0.256', 751.0),
            ('0.512', 751.0),
            ('1.024', 751.0),
            ('2.048', 751.0),
            ('4.096', 751.0),
            ('8.192', 751.0),
            ('+Inf', 751.0),
        ],
        sum_value=0.3097010759999998,
    )

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)

    current_metric = metrics[0]
    # in metrics with more than one label
    # the labels don't always get parsed in a deterministic order
    # deconstruct the metric to ensure it's equal
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(
        current_metric.samples, key=lambda i: i[0]
    )


def test_decumulate_histogram_buckets(p_check, mocked_prometheus_scraper_config):
    # buckets are not necessary ordered
    text_data = (
        '# HELP rest_client_request_latency_seconds Request latency in seconds. Broken down by verb and URL.\n'
        '# TYPE rest_client_request_latency_seconds histogram\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.004"} 702\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.001"} 254\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.002"} 621\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.008"} 727\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.016"} 738\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.032"} 744\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.064"} 748\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.128"} 754\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.256"} 755\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.512"} 755\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="+Inf"} 755\n'
        'rest_client_request_latency_seconds_sum{url="http://127.0.0.1:8080/api",verb="GET"} 2.185820220000001\n'
        'rest_client_request_latency_seconds_count{url="http://127.0.0.1:8080/api",verb="GET"} 755\n'
    )

    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)

    expected_metric = HistogramMetricFamily(
        'rest_client_request_latency_seconds_bucket', 'Request latency in seconds. Broken down by verb and URL.'
    )
    expected_metric.samples = [
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.004', 'lower_bound': '0.002', 'verb': 'GET'},
            81.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.001', 'lower_bound': '0', 'verb': 'GET'},
            254.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.002', 'lower_bound': '0.001', 'verb': 'GET'},
            367.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.008', 'lower_bound': '0.004', 'verb': 'GET'},
            25.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.016', 'lower_bound': '0.008', 'verb': 'GET'},
            11.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.032', 'lower_bound': '0.016', 'verb': 'GET'},
            6.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.064', 'lower_bound': '0.032', 'verb': 'GET'},
            4.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.128', 'lower_bound': '0.064', 'verb': 'GET'},
            6.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.256', 'lower_bound': '0.128', 'verb': 'GET'},
            1.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '0.512', 'lower_bound': '0.256', 'verb': 'GET'},
            0.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '+Inf', 'lower_bound': '0.512', 'verb': 'GET'},
            0.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_sum',
            {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'},
            2.185820220000001,
        ),
        Sample('rest_client_request_latency_seconds_count', {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'}, 755.0),
    ]

    current_metric = metrics[0]
    check._decumulate_histogram_buckets(current_metric)

    assert sorted(expected_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])


def test_decumulate_histogram_buckets_single_bucket(p_check, mocked_prometheus_scraper_config):
    # buckets are not necessary ordered
    text_data = (
        '# HELP rest_client_request_latency_seconds Request latency in seconds. Broken down by verb and URL.\n'
        '# TYPE rest_client_request_latency_seconds histogram\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="+Inf"} 755\n'
        'rest_client_request_latency_seconds_sum{url="http://127.0.0.1:8080/api",verb="GET"} 2.185820220000001\n'
        'rest_client_request_latency_seconds_count{url="http://127.0.0.1:8080/api",verb="GET"} 755\n'
    )

    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)

    expected_metric = HistogramMetricFamily(
        'rest_client_request_latency_seconds_bucket', 'Request latency in seconds. Broken down by verb and URL.'
    )
    expected_metric.samples = [
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '+Inf', 'lower_bound': '0', 'verb': 'GET'},
            755.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_sum',
            {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'},
            2.185820220000001,
        ),
        Sample('rest_client_request_latency_seconds_count', {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'}, 755.0),
    ]

    current_metric = metrics[0]
    check._decumulate_histogram_buckets(current_metric)

    assert sorted(expected_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])


def test_compute_bucket_hash(p_check):
    check = p_check

    # two different buckets should have the same hash for the same other tags values
    tags1 = {"url": "http://127.0.0.1:8080/api", "verb": "GET", "le": "1"}
    tags2 = {"url": "http://127.0.0.1:8080/api", "verb": "GET", "le": "2"}
    assert check._compute_bucket_hash(tags1) == check._compute_bucket_hash(tags2)

    # tag order should not matter
    tags3 = {"verb": "GET", "le": "+inf", "url": "http://127.0.0.1:8080/api"}
    assert check._compute_bucket_hash(tags1) == check._compute_bucket_hash(tags3)

    # changing a tag value should change the context hash
    tags4 = {"url": "http://127.0.0.1:8080/api", "verb": "DELETE", "le": "1"}
    assert check._compute_bucket_hash(tags1) != check._compute_bucket_hash(tags4)


def test_decumulate_histogram_buckets_multiple_contexts(p_check, mocked_prometheus_scraper_config):
    # buckets are not necessary ordered
    text_data = (
        '# HELP rest_client_request_latency_seconds Request latency in seconds. Broken down by verb and URL.\n'
        '# TYPE rest_client_request_latency_seconds histogram\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="1"} 100\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="2"} 200\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="+Inf"} 300\n'
        'rest_client_request_latency_seconds_sum{url="http://127.0.0.1:8080/api",verb="GET"} 256\n'
        'rest_client_request_latency_seconds_count{url="http://127.0.0.1:8080/api",verb="GET"} 300\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="POST",le="1"} 50\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="POST",le="2"} 100\n'
        'rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="POST",le="+Inf"} 150\n'
        'rest_client_request_latency_seconds_sum{url="http://127.0.0.1:8080/api",verb="POST"} 200\n'
        'rest_client_request_latency_seconds_count{url="http://127.0.0.1:8080/api",verb="POST"} 150\n'
    )

    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)

    expected_metric = HistogramMetricFamily(
        'rest_client_request_latency_seconds_bucket', 'Request latency in seconds. Broken down by verb and URL.'
    )

    expected_metric.samples = [
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '1', 'lower_bound': '0', 'verb': 'GET'},
            100.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '2', 'lower_bound': '1.0', 'verb': 'GET'},
            100.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '+Inf', 'lower_bound': '2.0', 'verb': 'GET'},
            100.0,
        ),
        Sample('rest_client_request_latency_seconds_sum', {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'}, 256.0),
        Sample('rest_client_request_latency_seconds_count', {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'}, 300.0),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '1', 'lower_bound': '0', 'verb': 'POST'},
            50.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '2', 'lower_bound': '1.0', 'verb': 'POST'},
            50.0,
        ),
        Sample(
            'rest_client_request_latency_seconds_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '+Inf', 'lower_bound': '2.0', 'verb': 'POST'},
            50.0,
        ),
        Sample('rest_client_request_latency_seconds_sum', {'url': 'http://127.0.0.1:8080/api', 'verb': 'POST'}, 200.0),
        Sample(
            'rest_client_request_latency_seconds_count', {'url': 'http://127.0.0.1:8080/api', 'verb': 'POST'}, 150.0
        ),
    ]

    current_metric = metrics[0]
    check._decumulate_histogram_buckets(current_metric)

    assert sorted(expected_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])


def test_decumulate_histogram_buckets_negative_buckets(p_check, mocked_prometheus_scraper_config):
    text_data = (
        '# HELP random_histogram Nonsense histogram.\n'
        '# TYPE random_histogram histogram\n'
        'random_histogram_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="-Inf"} 0\n'
        'random_histogram_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="-10.0"} 50\n'
        'random_histogram_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="-2.0"} 55\n'
        'random_histogram_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="15.0"} 65\n'
        'random_histogram_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="+Inf"} 70\n'
        'random_histogram_sum{url="http://127.0.0.1:8080/api",verb="GET"} 3.14\n'
        'random_histogram_count{url="http://127.0.0.1:8080/api",verb="GET"} 70\n'
    )

    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)

    expected_metric = HistogramMetricFamily('random_histogram_bucket', 'Nonsense histogram.')
    expected_metric.samples = [
        Sample(
            'random_histogram_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '-Inf', 'lower_bound': '-inf', 'verb': 'GET'},
            0.0,
        ),
        Sample(
            'random_histogram_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '-10.0', 'lower_bound': '-inf', 'verb': 'GET'},
            50.0,
        ),
        Sample(
            'random_histogram_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '-2.0', 'lower_bound': '-10.0', 'verb': 'GET'},
            5.0,
        ),
        Sample(
            'random_histogram_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '15.0', 'lower_bound': '-2.0', 'verb': 'GET'},
            10.0,
        ),
        Sample(
            'random_histogram_bucket',
            {'url': 'http://127.0.0.1:8080/api', 'le': '+Inf', 'lower_bound': '15.0', 'verb': 'GET'},
            5.0,
        ),
        Sample('random_histogram_sum', {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'}, 3.14),
        Sample('random_histogram_count', {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'}, 70.0),
    ]

    current_metric = metrics[0]
    check._decumulate_histogram_buckets(current_metric)

    assert sorted(expected_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])


def test_decumulate_histogram_buckets_no_buckets(p_check, mocked_prometheus_scraper_config):
    # buckets are not necessary ordered
    text_data = (
        '# HELP rest_client_request_latency_seconds Request latency in seconds. Broken down by verb and URL.\n'
        '# TYPE rest_client_request_latency_seconds histogram\n'
        'rest_client_request_latency_seconds_sum{url="http://127.0.0.1:8080/api",verb="GET"} 2.185820220000001\n'
        'rest_client_request_latency_seconds_count{url="http://127.0.0.1:8080/api",verb="GET"} 755\n'
    )

    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)

    expected_metric = HistogramMetricFamily(
        'random_histogram_bucket', 'Request latency in seconds. Broken down by verb and URL.'
    )
    expected_metric.samples = [
        Sample(
            'rest_client_request_latency_seconds_sum',
            {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'},
            2.185820220000001,
        ),
        Sample('rest_client_request_latency_seconds_count', {'url': 'http://127.0.0.1:8080/api', 'verb': 'GET'}, 755.0),
    ]

    current_metric = metrics[0]
    check._decumulate_histogram_buckets(current_metric)

    assert sorted(expected_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])


def test_parse_one_summary(p_check, mocked_prometheus_scraper_config):
    """
    name: "http_response_size_bytes"
    help: "The HTTP response sizes in bytes."
    type: SUMMARY
    metric {
      label {
        name: "handler"
        value: "prometheus"
      }
      summary {
        sample_count: 5
        sample_sum: 120512.0
        quantile {
          quantile: 0.5
          value: 24547.0
        }
        quantile {
          quantile: 0.9
          value: 25763.0
        }
        quantile {
          quantile: 0.99
          value: 25763.0
        }
      }
    }
    """
    text_data = (
        '# HELP http_response_size_bytes The HTTP response sizes in bytes.\n'
        '# TYPE http_response_size_bytes summary\n'
        'http_response_size_bytes{handler="prometheus",quantile="0.5"} 24547\n'
        'http_response_size_bytes{handler="prometheus",quantile="0.9"} 25763\n'
        'http_response_size_bytes{handler="prometheus",quantile="0.99"} 25763\n'
        'http_response_size_bytes_sum{handler="prometheus"} 120512\n'
        'http_response_size_bytes_count{handler="prometheus"} 5\n'
    )

    expected_etcd_metric = SummaryMetricFamily(
        'http_response_size_bytes', 'The HTTP response sizes in bytes.', labels=["handler"]
    )
    expected_etcd_metric.add_metric(["prometheus"], 5.0, 120512.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"handler": "prometheus", "quantile": "0.5"}, 24547.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"handler": "prometheus", "quantile": "0.9"}, 25763.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"handler": "prometheus", "quantile": "0.99"}, 25763.0)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(
        current_metric.samples, key=lambda i: i[0]
    )


def test_parse_one_summary_with_no_quantile(p_check, mocked_prometheus_scraper_config):
    """
    name: "http_response_size_bytes"
    help: "The HTTP response sizes in bytes."
    type: SUMMARY
    metric {
      label {
        name: "handler"
        value: "prometheus"
      }
      summary {
        sample_count: 5
        sample_sum: 120512.0
      }
    }
    """
    text_data = (
        '# HELP http_response_size_bytes The HTTP response sizes in bytes.\n'
        '# TYPE http_response_size_bytes summary\n'
        'http_response_size_bytes_sum{handler="prometheus"} 120512\n'
        'http_response_size_bytes_count{handler="prometheus"} 5\n'
    )

    expected_etcd_metric = SummaryMetricFamily(
        'http_response_size_bytes', 'The HTTP response sizes in bytes.', labels=["handler"]
    )
    expected_etcd_metric.add_metric(["prometheus"], 5.0, 120512.0)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(
        current_metric.samples, key=lambda i: i[0]
    )


def test_parse_two_summaries_with_labels(p_check, mocked_prometheus_scraper_config):
    text_data = (
        '# HELP http_response_size_bytes The HTTP response sizes in bytes.\n'
        '# TYPE http_response_size_bytes summary\n'
        'http_response_size_bytes{from="internet",handler="prometheus",quantile="0.5"} 24547\n'
        'http_response_size_bytes{from="internet",handler="prometheus",quantile="0.9"} 25763\n'
        'http_response_size_bytes{from="internet",handler="prometheus",quantile="0.99"} 25763\n'
        'http_response_size_bytes_sum{from="internet",handler="prometheus"} 120512\n'
        'http_response_size_bytes_count{from="internet",handler="prometheus"} 5\n'
        'http_response_size_bytes{from="cluster",handler="prometheus",quantile="0.5"} 24615\n'
        'http_response_size_bytes{from="cluster",handler="prometheus",quantile="0.9"} 24627\n'
        'http_response_size_bytes{from="cluster",handler="prometheus",quantile="0.99"} 24627\n'
        'http_response_size_bytes_sum{from="cluster",handler="prometheus"} 94913\n'
        'http_response_size_bytes_count{from="cluster",handler="prometheus"} 4\n'
    )

    expected_etcd_metric = SummaryMetricFamily(
        'http_response_size_bytes', 'The HTTP response sizes in bytes.', labels=["from", "handler"]
    )
    expected_etcd_metric.add_metric(["internet", "prometheus"], 5.0, 120512.0)
    expected_etcd_metric.add_sample(
        "http_response_size_bytes", {"from": "internet", "handler": "prometheus", "quantile": "0.5"}, 24547.0
    )
    expected_etcd_metric.add_sample(
        "http_response_size_bytes", {"from": "internet", "handler": "prometheus", "quantile": "0.9"}, 25763.0
    )
    expected_etcd_metric.add_sample(
        "http_response_size_bytes", {"from": "internet", "handler": "prometheus", "quantile": "0.99"}, 25763.0
    )
    expected_etcd_metric.add_metric(["cluster", "prometheus"], 4.0, 94913.0)
    expected_etcd_metric.add_sample(
        "http_response_size_bytes", {"from": "cluster", "handler": "prometheus", "quantile": "0.5"}, 24615.0
    )
    expected_etcd_metric.add_sample(
        "http_response_size_bytes", {"from": "cluster", "handler": "prometheus", "quantile": "0.9"}, 24627.0
    )
    expected_etcd_metric.add_sample(
        "http_response_size_bytes", {"from": "cluster", "handler": "prometheus", "quantile": "0.99"}, 24627.0
    )

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))

    assert 1 == len(metrics)

    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(
        current_metric.samples, key=lambda i: i[0]
    )


def test_parse_one_summary_with_none_values(p_check, mocked_prometheus_scraper_config):
    text_data = (
        '# HELP http_response_size_bytes The HTTP response sizes in bytes.\n'
        '# TYPE http_response_size_bytes summary\n'
        'http_response_size_bytes{handler="prometheus",quantile="0.5"} NaN\n'
        'http_response_size_bytes{handler="prometheus",quantile="0.9"} NaN\n'
        'http_response_size_bytes{handler="prometheus",quantile="0.99"} NaN\n'
        'http_response_size_bytes_sum{handler="prometheus"} 0\n'
        'http_response_size_bytes_count{handler="prometheus"} 0\n'
    )

    expected_etcd_metric = SummaryMetricFamily(
        'http_response_size_bytes', 'The HTTP response sizes in bytes.', labels=["handler"]
    )
    expected_etcd_metric.add_metric(["prometheus"], 0.0, 0.0)
    expected_etcd_metric.add_sample(
        "http_response_size_bytes", {"handler": "prometheus", "quantile": "0.5"}, float('nan')
    )
    expected_etcd_metric.add_sample(
        "http_response_size_bytes", {"handler": "prometheus", "quantile": "0.9"}, float('nan')
    )
    expected_etcd_metric.add_sample(
        "http_response_size_bytes", {"handler": "prometheus", "quantile": "0.99"}, float('nan')
    )

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, headers={'Content-Type': text_content_type})
    check = p_check
    metrics = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))
    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    # As the NaN value isn't supported when we are calling assertEqual
    assert math.isnan(current_metric.samples[0][2])
    assert math.isnan(current_metric.samples[1][2])
    assert math.isnan(current_metric.samples[2][2])


def test_ignore_metric(aggregator, mocked_prometheus_check, ref_gauge):
    """
    Test that an ignored metric is properly discarded.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    instance['ignore_metrics'] = ['process_virtual_memory_bytes']

    config = check.get_scraper_config(instance)
    config['_dry_run'] = False

    check.process_metric(ref_gauge, config)

    aggregator.assert_metric('prometheus.process.vm.bytes', count=0)


def test_ignore_metric_wildcard(aggregator, mocked_prometheus_check, ref_gauge):
    """
    Test that metric that matched the ignored metrics pattern is properly discarded.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    instance['ignore_metrics'] = ['process_virtual_*']

    config = check.get_scraper_config(instance)
    config['_dry_run'] = False

    check.process_metric(ref_gauge, config)

    aggregator.assert_metric('prometheus.process.vm.bytes', count=0)


def test_ignore_metrics_multiple_wildcards(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, text_data
):
    """
    Test that metrics that matched an ignored metrics pattern is properly discarded.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    instance['_dry_run'] = False
    instance['metrics'] = [
        {
            # Ignored
            'go_memstats_mspan_inuse_bytes': 'go_memstats.mspan.inuse_bytes',
            'go_memstats_mallocs_total': 'go_memstats.mallocs.total',
            'go_memstats_mspan_sys_bytes': 'go_memstats.mspan.sys_bytes',
            'go_memstats_alloc_bytes': 'go_memstats.alloc_bytes',
            'go_memstats_gc_sys_bytes': 'go_memstats.gc.sys_bytes',
            'go_memstats_buck_hash_sys_bytes': 'go_memstats.buck_hash.sys_bytes',
            # Not ignored
            'go_memstats_mcache_sys_bytes': 'go_memstats.mcache.sys_bytes',
            'go_memstats_heap_released_bytes_total': 'go_memstats.heap.released.bytes_total',
        }
    ]
    instance['ignore_metrics'] = [
        'go_memstats_mallocs_total',
        'go_memstats_mspan_*',
        '*alloc*',
        '*gc_sys_bytes',
        'go_memstats_*_hash_sys_bytes',
    ]

    config = check.create_scraper_configuration(instance)

    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': text_content_type}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check.process(config)

        # Make sure metrics are ignored
        aggregator.assert_metric('prometheus.go_memstats.mspan.inuse_bytes', count=0)
        aggregator.assert_metric('prometheus.go_memstats.mallocs.total', count=0)
        aggregator.assert_metric('prometheus.go_memstats.mspan.sys_bytes', count=0)
        aggregator.assert_metric('prometheus.go_memstats.alloc_bytes', count=0)
        aggregator.assert_metric('prometheus.go_memstats.gc.sys_bytes', count=0)
        aggregator.assert_metric('prometheus.go_memstats.buck_hash.sys_bytes', count=0)

        # Make sure we don't ignore other metrics
        aggregator.assert_metric('prometheus.go_memstats.mcache.sys_bytes', count=1)
        aggregator.assert_metric('prometheus.go_memstats.heap.released.bytes_total', count=1)
        aggregator.assert_all_metrics_covered()


def test_gauge_with_ignore_label_wildcard(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """submitting metrics that contain labels should result in tags on the gauge call"""
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['worker', 'node']
    )
    ref_gauge.add_metric(['worker_1', 'foo'], 54927360.0)
    ref_gauge.add_metric(['worker_2', 'bar'], 1009345.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['ignore_metrics_by_labels'] = {'worker': ['*']}
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric_name, ref_gauge, mocked_prometheus_scraper_config)
    check.log.debug.assert_called_with(
        'Skipping metric `%s` due to label key matching: %s', 'process.vm.bytes', 'worker'
    )
    # Ignored metric
    aggregator.assert_metric('prometheus.process.vm.bytes', count=0, tags=['worker:worker_1', 'node:foo'])
    aggregator.assert_metric('prometheus.process.vm.bytes', count=0, tags=['worker:worker_2', 'node:bar'])


def test_gauge_with_ignore_label_value(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """submitting metrics that contain labels should result in tags on the gauge call"""
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['worker', 'node', 'worker_name']
    )
    ref_gauge.add_metric(['worker_1', 'foo', 'joe'], 54927360.0)
    ref_gauge.add_metric(['worker_2', 'bar', 'tom'], 1009345.0)
    ref_gauge.add_metric(['worker_3', 'bar', 'worker_1'], 45000.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['ignore_metrics_by_labels'] = {'worker': ['worker_1']}
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric_name, ref_gauge, mocked_prometheus_scraper_config)

    check.log.debug.assert_called_with(
        'Skipping metric `%s` due to label `%s` value matching: %s', 'process.vm.bytes', 'worker', 'worker_1'
    )
    # Ignored metric
    aggregator.assert_metric(
        'prometheus.process.vm.bytes', count=0, tags=['worker:worker_1', 'node:foo', 'worker_name:joe']
    )

    # Not ignored metric
    aggregator.assert_metric(
        'prometheus.process.vm.bytes', count=1, tags=['worker:worker_2', 'node:bar', 'worker_name:tom']
    )
    aggregator.assert_metric(
        'prometheus.process.vm.bytes', count=1, tags=['worker:worker_3', 'node:bar', 'worker_name:worker_1']
    )


def test_gauge_with_invalid_ignore_label_value(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """submitting metrics that contain labels should result in tags on the gauge call"""
    ref_gauge = GaugeMetricFamily(
        'process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['worker', 'node']
    )
    ref_gauge.add_metric(['worker_2', 'bar'], 1009345.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['ignore_metrics_by_labels'] = {'worker': []}
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check.submit_openmetric(metric_name, ref_gauge, mocked_prometheus_scraper_config)
    check.log.debug.assert_called_with(
        "Skipping filter label `%s` with an empty values list, did you mean to use '*' wildcard?", 'worker'
    )


def test_metrics_with_ignore_label_values(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, text_data
):
    """
    Test that metrics that matched an ignored label values is properly discarded.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    instance['metrics'] = [
        {
            # Ignore counter by label values 'system': ['auth', 'recursive']
            'skydns_skydns_dns_error_count_total': 'skydns.dns.error.count',
            # Ignore counter by label key 'cache'
            'skydns_skydns_dns_cachemiss_count_total': 'skydns.dns.cache_missed',
            # Expected metric
            'go_memstats_mspan_inuse_bytes': 'go_memstats.mspan.inuse_bytes',
        }
    ]
    instance['ignore_metrics_by_labels'] = {'system': ['auth', 'recursive'], 'cache': ['*']}
    config = check.create_scraper_configuration(instance)
    expected_tags = ['cause:nxdomain']
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': text_content_type}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check.process(config)

        # Make sure metrics are ignored
        aggregator.assert_metric('prometheus.skydns.dns.error.count', count=0, tags=expected_tags + ['system:auth'])
        aggregator.assert_metric(
            'prometheus.skydns.dns.error.count', count=0, tags=expected_tags + ['system:recursive']
        )
        aggregator.assert_metric('prometheus.skydns.dns.cache_missed', count=0)
        # Make sure we don't ignore other metrics
        aggregator.assert_metric('prometheus.skydns.dns.error.count', count=1, tags=expected_tags + ['system:reverse'])
        aggregator.assert_metric('prometheus.go_memstats.mspan.inuse_bytes', count=1)

        aggregator.assert_all_metrics_covered()


def test_match_metric_wildcard(aggregator, mocked_prometheus_check, ref_gauge):
    """
    Test that a matched metric is properly collected.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)

    config = check.get_scraper_config(instance)
    config['_dry_run'] = False

    check.process_metric(ref_gauge, config)

    aggregator.assert_metric('prometheus.process.vm.bytes', count=1)


def test_match_metrics_multiple_wildcards(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, text_data
):
    """
    Test that matched metric patterns are properly collected.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    instance['_dry_run'] = False
    instance['metrics'] = [
        {'go_memstats_mcache_*': '', 'go_memstats_heap_released_bytes_total': 'go_memstats.heap.released.bytes_total'},
        '*_lookups_total*',
        'go_memstats_alloc*',
    ]

    config = check.create_scraper_configuration(instance)

    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': text_content_type}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check.process(config)

        aggregator.assert_metric('prometheus.go_memstats_mcache_inuse_bytes', count=1)
        aggregator.assert_metric('prometheus.go_memstats_mcache_sys_bytes', count=1)
        aggregator.assert_metric('prometheus.go_memstats.heap.released.bytes_total', count=1)
        aggregator.assert_metric('prometheus.go_memstats_alloc_bytes', count=1)
        aggregator.assert_metric('prometheus.go_memstats_alloc_bytes_total', count=1)
        aggregator.assert_metric('prometheus.go_memstats_lookups_total', count=1)
        aggregator.assert_all_metrics_covered()


def test_label_joins(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """Tests label join on text format"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_global_labels': {'label_to_match': '*', 'labels_to_get': ['*']},
        'kube_local_labels': {'labels_to_match': ['*'], 'labels_to_get': ['foo']},
        'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node', 'pod_ip']},
        'kube_pod_labels': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['*']},
        'kube_deployment_labels': {
            'label_to_match': ['deployment'],
            'labels_to_get': [
                'label_addonmanager_kubernetes_io_mode',
                'label_k8s_app',
                'label_kubernetes_io_cluster_service',
            ],
        },
    }

    mocked_prometheus_scraper_config['metrics_mapper'] = {
        'kube_pod_status_ready': 'pod.ready',
        'kube_pod_status_scheduled': 'pod.scheduled',
        'kube_deployment_status_replicas': 'deploy.replicas.available',
    }

    # dry run to build mapping
    check.process(mocked_prometheus_scraper_config)

    # run with submit
    check.process(mocked_prometheus_scraper_config)

    # check a bunch of metrics
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:event-exporter-v0.1.7-958884745-qgnbw',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.14',
            'label_k8s_app:event-exporter',
            'label_pod_template_hash:958884745',
            'label_version:v0.1.7',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:fluentd-gcp-v2.0.9-6dj58',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.132.0.7',
            'label_controller_revision_hash:3483772856',
            'label_k8s_app:fluentd-gcp',
            'label_kubernetes_io_cluster_service:true',
            'label_pod_template_generation:1',
            'label_version:v2.0.9',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:fluentd-gcp-v2.0.9-z348z',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.132.0.14',
            'label_controller_revision_hash:3483772856',
            'label_k8s_app:fluentd-gcp',
            'label_kubernetes_io_cluster_service:true',
            'label_pod_template_generation:1',
            'label_version:v2.0.9',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:heapster-v1.4.3-2027615481-lmjm5',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.32.5.7',
            'label_k8s_app:heapster',
            'label_pod_template_hash:2027615481',
            'label_version:v1.4.3',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:kube-dns-3092422022-lvrmx',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.10',
            'label_k8s_app:kube-dns',
            'label_pod_template_hash:3092422022',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:kube-dns-3092422022-x0tjx',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.9',
            'label_k8s_app:kube-dns',
            'label_pod_template_hash:3092422022',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:kube-dns-autoscaler-97162954-mf6d3',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.32.5.6',
            'label_k8s_app:kube-dns-autoscaler',
            'label_pod_template_hash:97162954',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:kube-proxy-gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.132.0.7',
            'label_component:kube-proxy',
            'label_tier:node',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.scheduled',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:ungaged-panther-kube-state-metrics-3918010230-64xwc',
            'namespace:default',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.32.5.45',
            'label_app:kube-state-metrics',
            'label_pod_template_hash:3918010230',
            'label_release:ungaged-panther',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.scheduled',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:event-exporter-v0.1.7-958884745-qgnbw',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.14',
            'label_k8s_app:event-exporter',
            'label_pod_template_hash:958884745',
            'label_version:v0.1.7',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.scheduled',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:fluentd-gcp-v2.0.9-6dj58',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.132.0.7',
            'label_controller_revision_hash:3483772856',
            'label_k8s_app:fluentd-gcp',
            'label_kubernetes_io_cluster_service:true',
            'label_pod_template_generation:1',
            'label_version:v2.0.9',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.scheduled',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:fluentd-gcp-v2.0.9-z348z',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.132.0.14',
            'label_controller_revision_hash:3483772856',
            'label_k8s_app:fluentd-gcp',
            'label_kubernetes_io_cluster_service:true',
            'label_pod_template_generation:1',
            'label_version:v2.0.9',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.scheduled',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:heapster-v1.4.3-2027615481-lmjm5',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.32.5.7',
            'label_k8s_app:heapster',
            'label_pod_template_hash:2027615481',
            'label_version:v1.4.3',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.scheduled',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:kube-dns-3092422022-lvrmx',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.10',
            'label_k8s_app:kube-dns',
            'label_pod_template_hash:3092422022',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.scheduled',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'pod:kube-dns-3092422022-x0tjx',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.9',
            'label_k8s_app:kube-dns',
            'label_pod_template_hash:3092422022',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.deploy.replicas.available',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'namespace:kube-system',
            'deployment:event-exporter-v0.1.7',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_k8s_app:event-exporter',
            'label_kubernetes_io_cluster_service:true',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.deploy.replicas.available',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'namespace:kube-system',
            'deployment:heapster-v1.4.3',
            'label_k8s_app:heapster',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_kubernetes_io_cluster_service:true',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.deploy.replicas.available',
        2.0,
        tags=[
            'leader:true',
            'foo:bar',
            'namespace:kube-system',
            'deployment:kube-dns',
            'label_kubernetes_io_cluster_service:true',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_k8s_app:kube-dns',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.deploy.replicas.available',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'namespace:kube-system',
            'deployment:kube-dns-autoscaler',
            'label_kubernetes_io_cluster_service:true',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_k8s_app:kube-dns-autoscaler',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.deploy.replicas.available',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'namespace:kube-system',
            'deployment:kubernetes-dashboard',
            'label_kubernetes_io_cluster_service:true',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_k8s_app:kubernetes-dashboard',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.deploy.replicas.available',
        1.0,
        tags=[
            'leader:true',
            'foo:bar',
            'namespace:kube-system',
            'deployment:l7-default-backend',
            'label_k8s_app:glbc',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_kubernetes_io_cluster_service:true',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.deploy.replicas.available',
        1.0,
        tags=['leader:true', 'foo:bar', 'namespace:kube-system', 'deployment:tiller-deploy'],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.deploy.replicas.available',
        1.0,
        tags=['leader:true', 'foo:bar', 'namespace:default', 'deployment:ungaged-panther-kube-state-metrics'],
        count=1,
    )


def test_label_joins_gc(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """Tests label join GC on text format"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node', 'pod_ip']},
        'kube_persistentvolumeclaim_info': {
            'labels_to_match': ['persistentvolumeclaim', 'namespace'],
            'labels_to_get': ['storageclass'],
        },
    }
    mocked_prometheus_scraper_config['metrics_mapper'] = {'kube_pod_status_ready': 'pod.ready'}
    # dry run to build mapping
    check.process(mocked_prometheus_scraper_config)
    # run with submit
    check.process(mocked_prometheus_scraper_config)

    # check a bunch of metrics
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'pod:fluentd-gcp-v2.0.9-6dj58',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.132.0.7',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'pod:fluentd-gcp-v2.0.9-z348z',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.132.0.14',
        ],
        count=1,
    )

    assert 15 == len(mocked_prometheus_scraper_config['_label_mapping']['pod'])
    text_data = mock_get.replace('dd-agent-62bgh', 'dd-agent-1337')
    pvc_replace = re.compile(r'^kube_persistentvolumeclaim_.*\n', re.MULTILINE)
    text_data = pvc_replace.sub('', text_data)

    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': text_content_type}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check.process(mocked_prometheus_scraper_config)
        assert 'dd-agent-1337' in mocked_prometheus_scraper_config['_label_mapping']['pod']
        assert 'dd-agent-62bgh' not in mocked_prometheus_scraper_config['_label_mapping']['pod']
        assert 15 == len(mocked_prometheus_scraper_config['_label_mapping']['pod'])


def test_label_joins_missconfigured(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """Tests label join missconfigured label is ignored"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node', 'not_existing']}
    }
    mocked_prometheus_scraper_config['metrics_mapper'] = {'kube_pod_status_ready': 'pod.ready'}

    # dry run to build mapping
    check.process(mocked_prometheus_scraper_config)
    # run with submit
    check.process(mocked_prometheus_scraper_config)

    # check a bunch of metrics
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'pod:fluentd-gcp-v2.0.9-6dj58',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
        ],
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'pod:fluentd-gcp-v2.0.9-z348z',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
        ],
        count=1,
    )


def test_label_join_not_existing(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """Tests label join on non existing matching label is ignored"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_pod_info': {'label_to_match': 'not_existing', 'labels_to_get': ['node', 'pod_ip']}
    }
    mocked_prometheus_scraper_config['metrics_mapper'] = {'kube_pod_status_ready': 'pod.ready'}
    # dry run to build mapping
    check.process(mocked_prometheus_scraper_config)
    # run with submit
    check.process(mocked_prometheus_scraper_config)
    # check a bunch of metrics
    aggregator.assert_metric(
        'ksm.pod.ready', 1.0, ['pod:fluentd-gcp-v2.0.9-6dj58', 'namespace:kube-system', 'condition:true'], count=1
    )
    aggregator.assert_metric(
        'ksm.pod.ready', 1.0, tags=['pod:fluentd-gcp-v2.0.9-z348z', 'namespace:kube-system', 'condition:true'], count=1
    )


def test_label_join_metric_not_existing(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get
):
    """Tests label join on non existing metric is ignored"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'not_existing': {'label_to_match': 'pod', 'labels_to_get': ['node', 'pod_ip']}
    }
    mocked_prometheus_scraper_config['metrics_mapper'] = {'kube_pod_status_ready': 'pod.ready'}
    # dry run to build mapping
    check.process(mocked_prometheus_scraper_config)
    # run with submit
    check.process(mocked_prometheus_scraper_config)
    # check a bunch of metrics
    aggregator.assert_metric(
        'ksm.pod.ready', 1.0, tags=['pod:fluentd-gcp-v2.0.9-6dj58', 'namespace:kube-system', 'condition:true'], count=1
    )
    aggregator.assert_metric(
        'ksm.pod.ready', 1.0, tags=['pod:fluentd-gcp-v2.0.9-z348z', 'namespace:kube-system', 'condition:true'], count=1
    )


def test_label_join_with_hostname(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """Tests label join and hostname override on a metric"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node']}
    }
    mocked_prometheus_scraper_config['label_to_hostname'] = 'node'
    mocked_prometheus_scraper_config['metrics_mapper'] = {'kube_pod_status_ready': 'pod.ready'}
    # dry run to build mapping
    check.process(mocked_prometheus_scraper_config)
    # run with submit
    check.process(mocked_prometheus_scraper_config)
    # check a bunch of metrics
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'pod:fluentd-gcp-v2.0.9-6dj58',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
        ],
        hostname='gke-foobar-test-kube-default-pool-9b4ff111-0kch',
        count=1,
    )
    aggregator.assert_metric(
        'ksm.pod.ready',
        1.0,
        tags=[
            'pod:fluentd-gcp-v2.0.9-z348z',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
        ],
        hostname='gke-foobar-test-kube-default-pool-9b4ff111-j75z',
        count=1,
    )


def test_label_join_state_change(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """
    This test checks that the label join picks up changes for already watched labels.
    If a phase changes for example, the tag should change as well.
    """
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        'kube_pod_status_phase': {'label_to_match': 'pod', 'labels_to_get': ['phase']},
    }
    mocked_prometheus_scraper_config['metrics_mapper'] = {'kube_pod_status_ready': 'pod.ready'}
    # dry run to build mapping
    check.process(mocked_prometheus_scraper_config)
    # run with submit
    check.process(mocked_prometheus_scraper_config)

    # check that 15 pods are in phase:Running
    assert 15 == len(mocked_prometheus_scraper_config['_label_mapping']['pod'])
    for _, tags in iteritems(mocked_prometheus_scraper_config['_label_mapping']['pod']):
        assert tags.get('phase') == 'Running'

    text_data = mock_get.replace(
        'kube_pod_status_phase{namespace="default",phase="Running",pod="dd-agent-62bgh"} 1',
        'kube_pod_status_phase{namespace="default",phase="Test",pod="dd-agent-62bgh"} 1',
    )

    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': text_content_type}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check.process(mocked_prometheus_scraper_config)
        assert 15 == len(mocked_prometheus_scraper_config['_label_mapping']['pod'])
        assert mocked_prometheus_scraper_config['_label_mapping']['pod']['dd-agent-62bgh']['phase'] == 'Test'


def test_label_to_match_single(benchmark, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """Tests label join and hostname override on a metric"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        '1': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        '2': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        '3': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        '4': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        '5': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        '6': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        '7': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        '8': {'label_to_match': 'pod', 'labels_to_get': ['node']},
        '9': {'label_to_match': 'pod', 'labels_to_get': ['node']},
    }
    mocked_prometheus_scraper_config['label_to_hostname'] = 'node'
    mocked_prometheus_scraper_config['metrics_mapper'] = {'kube_pod_status_ready': 'pod.ready'}

    @benchmark
    def run_check():
        # dry run to build mapping
        check.process(mocked_prometheus_scraper_config)
        # run with submit
        check.process(mocked_prometheus_scraper_config)


def test_label_to_match_multiple(benchmark, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """Tests label join and hostname override on a metric"""
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_pod_info': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        '1': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        '2': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        '3': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        '4': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        '5': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        '6': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        '7': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        '8': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        '9': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
    }
    mocked_prometheus_scraper_config['label_to_hostname'] = 'node'
    mocked_prometheus_scraper_config['metrics_mapper'] = {'kube_pod_status_ready': 'pod.ready'}

    @benchmark
    def run_check():
        # dry run to build mapping
        check.process(mocked_prometheus_scraper_config)
        # run with submit
        check.process(mocked_prometheus_scraper_config)


def test_health_service_check_ok(mock_get, aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """Tests endpoint health service check OK"""
    check = mocked_prometheus_check

    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['custom_tags'] = ['foo:bar']
    mocked_prometheus_scraper_config['_metric_tags'] = ['bar:foo']
    check.process(mocked_prometheus_scraper_config)

    aggregator.assert_service_check(
        'ksm.prometheus.health',
        status=OpenMetricsBaseCheck.OK,
        tags=['endpoint:http://fake.endpoint:10055/metrics', 'foo:bar'],
        count=1,
    )


def test_health_service_check_failing(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """Tests endpoint health service check failing"""
    check = mocked_prometheus_check

    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['custom_tags'] = ['foo:bar']
    mocked_prometheus_scraper_config['_metric_tags'] = ['bar:foo']
    with pytest.raises(requests.ConnectionError):
        check.process(mocked_prometheus_scraper_config)
    aggregator.assert_service_check(
        'ksm.prometheus.health',
        status=OpenMetricsBaseCheck.CRITICAL,
        tags=['endpoint:http://fake.endpoint:10055/metrics', 'foo:bar'],
        count=1,
    )


def test_text_filter_input(mocked_prometheus_check, mocked_prometheus_scraper_config):
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['_text_filter_blacklist'] = ["string1", "string2"]

    lines_in = [
        "line with string3",
        "line with string1",
        "line with string2",
        "line with string1 and string2",
        "line with string",
    ]
    expected_out = ["line with string3", "line with string"]

    filtered = list(check._text_filter_input(lines_in, mocked_prometheus_scraper_config))
    assert filtered == expected_out


@pytest.fixture()
def mock_filter_get():
    text_data = None
    f_name = os.path.join(FIXTURE_PATH, 'deprecated.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': text_content_type},
        ),
    ):
        yield text_data


class FilterOpenMetricsCheck(OpenMetricsBaseCheck):
    def _filter_metric(self, metric, scraper_config):
        return metric.documentation.startswith("(Deprecated)")


@pytest.fixture
def mocked_filter_openmetrics_check():
    check = FilterOpenMetricsCheck('prometheus_check', {}, {})
    check.log = logging.getLogger('datadog-prometheus.test')
    check.log.debug = mock.MagicMock()
    return check


@pytest.fixture
def mocked_filter_openmetrics_check_scraper_config(mocked_filter_openmetrics_check):
    yield mocked_filter_openmetrics_check.get_scraper_config(PROMETHEUS_CHECK_INSTANCE)


def test_filter_metrics(
    aggregator, mocked_filter_openmetrics_check, mocked_filter_openmetrics_check_scraper_config, mock_filter_get
):
    """Tests label join GC on text format"""
    check = mocked_filter_openmetrics_check
    mocked_filter_openmetrics_check_scraper_config['namespace'] = 'filter'
    mocked_filter_openmetrics_check_scraper_config['metrics_mapper'] = {
        'kube_pod_container_status_restarts': 'pod.restart',
        'kube_pod_container_status_restarts_old': 'pod.restart_old',
    }
    # dry run to build mapping
    check.process(mocked_filter_openmetrics_check_scraper_config)
    # run with submit
    check.process(mocked_filter_openmetrics_check_scraper_config)
    # check a bunch of metrics
    aggregator.assert_metric(
        'filter.pod.restart', tags=['pod:kube-dns-autoscaler-97162954-mf6d3', 'namespace:kube-system'], value=42
    )
    aggregator.assert_all_metrics_covered()


def test_metadata_default(mocked_openmetrics_check_factory, text_data, datadog_agent):
    instance = dict(OPENMETRICS_CHECK_INSTANCE)
    check = mocked_openmetrics_check_factory(instance)
    check.poll = mock.MagicMock(return_value=MockResponse(text_data, headers={'Content-Type': text_content_type}))

    check.check(instance)
    datadog_agent.assert_metadata_count(0)


def test_metadata_transformer(mocked_openmetrics_check_factory, text_data, datadog_agent):
    instance = dict(OPENMETRICS_CHECK_INSTANCE)
    instance['metadata_metric_name'] = 'kubernetes_build_info'
    instance['metadata_label_map'] = {'version': 'gitVersion'}
    check = mocked_openmetrics_check_factory(instance)
    check.poll = mock.MagicMock(return_value=MockResponse(text_data, headers={'Content-Type': text_content_type}))

    version_metadata = {
        'version.major': '1',
        'version.minor': '6',
        'version.patch': '0',
        'version.release': 'alpha.0.680',
        'version.build': '3872cb93abf948-dirty',
        'version.raw': 'v1.6.0-alpha.0.680+3872cb93abf948-dirty',
        'version.scheme': 'semver',
    }

    check.check(instance)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


def test_ssl_verify_not_raise_warning(caplog, mocked_openmetrics_check_factory, text_data):
    instance = {
        'prometheus_url': 'https://www.example.com',
        'metrics': [{'foo': 'bar'}],
        'namespace': 'openmetrics',
        'ssl_verify': False,
    }
    check = mocked_openmetrics_check_factory(instance)
    scraper_config = check.get_scraper_config(instance)

    with caplog.at_level(logging.DEBUG), mock.patch('requests.get', return_value=MockResponse('httpbin.org')):
        resp = check.send_request('https://httpbin.org/get', scraper_config)

    assert "httpbin.org" in resp.content.decode('utf-8')

    expected_message = 'An unverified HTTPS request is being made to https://httpbin.org/get'
    for _, _, message in caplog.record_tuples:
        assert message != expected_message


def test_send_request_with_dynamic_prometheus_url(caplog, mocked_openmetrics_check_factory, text_data):
    instance = {
        'prometheus_url': 'https://www.example.com',
        'metrics': [{'foo': 'bar'}],
        'namespace': 'openmetrics',
        'ssl_verify': False,
    }

    check = mocked_openmetrics_check_factory(instance)
    scraper_config = check.get_scraper_config(instance)

    # `prometheus_url` changed just before calling `send_request`
    scraper_config['prometheus_url'] = 'https://www.example.com/foo/bar'

    with caplog.at_level(logging.DEBUG), mock.patch('requests.get', return_value=MockResponse('httpbin.org')):
        resp = check.send_request('https://httpbin.org/get', scraper_config)

    assert "httpbin.org" in resp.content.decode('utf-8')

    expected_message = 'An unverified HTTPS request is being made to https://httpbin.org/get'
    for _, _, message in caplog.record_tuples:
        assert message != expected_message


def test_http_handler(mocked_openmetrics_check_factory):
    instance = {
        'prometheus_url': 'https://www.example.com',
        'metrics': [{'foo': 'bar'}],
        'namespace': 'openmetrics',
        'ssl_verify': False,
    }
    check = mocked_openmetrics_check_factory(instance)
    scraper_config = check.get_scraper_config(instance)

    http_handler = check.get_http_handler(scraper_config)

    assert http_handler.options['headers']['accept-encoding'] == 'gzip'
    assert http_handler.options['headers']['accept'] == 'text/plain'


def test_simple_type_overrides(aggregator, mocked_prometheus_check, text_data):
    """
    Test that metric type is overridden correctly.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    instance['type_overrides'] = {"process_virtual_memory_bytes": "counter"}

    # Make sure we don't send counters as gauges
    instance['send_monotonic_counter'] = True

    config = check.get_scraper_config(instance)
    config['_dry_run'] = False

    check.poll = mock.MagicMock(return_value=MockResponse(text_data, headers={'Content-Type': text_content_type}))
    check.process(config)

    aggregator.assert_metric('prometheus.process.vm.bytes', count=1, metric_type=aggregator.MONOTONIC_COUNT)

    assert len(check.config_map[FAKE_ENDPOINT]['_type_override_patterns']) == 0
    assert len(check.config_map[FAKE_ENDPOINT]['type_overrides']) == 1


def test_wildcard_type_overrides(aggregator, mocked_prometheus_check, text_data):
    """
    Test that metric type is overridden correctly with wildcard.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    instance['type_overrides'] = {"*_virtual_memory_*": "counter"}

    # Make sure we don't send counters as gauges
    instance['send_monotonic_counter'] = True

    config = check.get_scraper_config(instance)
    config['_dry_run'] = False

    check.poll = mock.MagicMock(return_value=MockResponse(text_data, headers={'Content-Type': text_content_type}))
    check.process(config)

    aggregator.assert_metric('prometheus.process.vm.bytes', count=1, metric_type=aggregator.MONOTONIC_COUNT)

    # assert the pattern was stored correctly
    assert len(check.config_map[FAKE_ENDPOINT]['_type_override_patterns']) == 1
    assert list(check.config_map[FAKE_ENDPOINT]['_type_override_patterns'].values())[0] == 'counter'
    assert len(check.config_map[FAKE_ENDPOINT]['type_overrides']) == 0


def test_empty_namespace(aggregator, mocked_prometheus_check, text_data, ref_gauge):
    """
    Test that metric type is overridden correctly with wildcard.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    instance['namespace'] = ''

    config = check.get_scraper_config(instance)
    config['_dry_run'] = False

    check.process_metric(ref_gauge, config)

    aggregator.assert_metric('process.vm.bytes', count=1)


def test_ignore_tags_match(aggregator, mocked_prometheus_check, ref_gauge):
    """
    Test that tags matching ignored tag patterns are properly discarded.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    all_tags = ['foo', 'foobar', 'bar', 'bar:baz', 'bar:bar']
    ignored_tags = ['foo', 'bar:baz']
    wanted_tags = ['bar', 'bar:bar']
    instance['tags'] = all_tags
    instance['ignore_tags'] = ignored_tags

    config = check.get_scraper_config(instance)
    config['_dry_run'] = False

    check.process_metric(ref_gauge, config)

    aggregator.assert_metric('prometheus.process.vm.bytes', tags=wanted_tags, count=1)


def test_ignore_tags_wildcard(aggregator, mocked_prometheus_check, ref_gauge):
    """
    Test that tags matching ignored tag patters with wildcards are properly discarded.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    all_tags = ['foo', 'foobar', 'bar', 'bar:baz', 'bar:bar']
    ignored_tags = ['foo*', '.*baz']
    wanted_tags = ['bar', 'bar:bar']
    instance['tags'] = all_tags
    instance['ignore_tags'] = ignored_tags

    config = check.get_scraper_config(instance)
    config['_dry_run'] = False

    check.process_metric(ref_gauge, config)

    aggregator.assert_metric('prometheus.process.vm.bytes', tags=wanted_tags, count=1)


def test_ignore_tags_regex(aggregator, mocked_prometheus_check, ref_gauge):
    """
    Test that tags matching ignored tag patters with regex are properly discarded.
    """
    check = mocked_prometheus_check
    instance = copy.deepcopy(PROMETHEUS_CHECK_INSTANCE)
    all_tags = ['foo', 'foobar', 'bar:baz', 'bar:bar']
    ignored_tags = ['^foo', '.+:bar$']
    wanted_tags = ['bar:baz']
    instance['tags'] = all_tags
    instance['ignore_tags'] = ignored_tags

    config = check.get_scraper_config(instance)
    config['_dry_run'] = False

    check.process_metric(ref_gauge, config)

    aggregator.assert_metric('prometheus.process.vm.bytes', tags=wanted_tags, count=1)


test_use_process_start_time_data = """\
# HELP go_memstats_alloc_bytes_total Total number of bytes allocated, even if freed.
# TYPE go_memstats_alloc_bytes_total counter
go_memstats_alloc_bytes_total 9.339544592e+09
# HELP skydns_skydns_dns_request_duration_seconds Histogram of the time (in seconds) each request took to resolve.
# TYPE skydns_skydns_dns_request_duration_seconds histogram
skydns_skydns_dns_request_duration_seconds_bucket{system="auth",le="10"} 1.359194e+06
skydns_skydns_dns_request_duration_seconds_bucket{system="auth",le="+Inf"} 1.359194e+06
skydns_skydns_dns_request_duration_seconds_sum{system="auth"} 44.31446715499896
skydns_skydns_dns_request_duration_seconds_count{system="auth"} 1.359194e+06
# HELP go_gc_duration_seconds A summary of the GC invocation durations.
# TYPE go_gc_duration_seconds summary
go_gc_duration_seconds{quantile="0"} 0.00036825700000000004
go_gc_duration_seconds{quantile="0.25"} 0.00041007200000000004
go_gc_duration_seconds{quantile="0.5"} 0.00043824300000000005
go_gc_duration_seconds{quantile="0.75"} 0.00048369000000000005
go_gc_duration_seconds{quantile="1"} 0.0025860830000000003
go_gc_duration_seconds_sum 1.154763349
go_gc_duration_seconds_count 2351
"""


def _make_test_use_process_start_time_data(process_start_time):
    test_data = test_use_process_start_time_data
    if process_start_time:
        if not test_data.endswith('\n'):
            test_data += '\n'
        test_data += "# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.\n"
        test_data += "# TYPE process_start_time_seconds gauge\n"
        for seq, pst in enumerate(process_start_time):
            label = '{pid="%d"}' % (seq,) if len(process_start_time) > 1 else ""
            test_data += "process_start_time_seconds%s %f\n" % (
                label,
                pst,
            )
    return test_data


@pytest.mark.parametrize(
    'use_process_start_time, send_distribution_buckets, expect_first_flush, agent_start_time, process_start_time',
    [
        (False, False, False, None, None),
        (True, False, True, 10, [20]),
        (True, False, False, 20, [10]),
        (True, False, False, 10, []),
        (True, False, True, 10, [20, 30, 40]),
        (True, False, False, 20, [10, 30, 40]),
        (False, True, False, None, None),
        (True, True, True, 10, [20]),
        (True, True, False, 20, [10]),
        (True, True, False, 10, []),
        (True, True, True, 10, [20, 30, 40]),
        (True, True, False, 20, [10, 30, 40]),
    ],
    ids=[
        "disabled",
        "enabled, agent is older",
        "enabled, agent is newer",
        "enabled, metric n/a",
        "enabled, many metrics, all newer",
        "enabled, many metrics, some newer",
        "with buckets, disabled",
        "with buckets, enabled, agent is older",
        "with buckets, enabled, agent is newer",
        "with buckets, enabled, metric n/a",
        "with buckets, enabled, many metrics, all newer",
        "with buckets, enabled, many metrics, some newer",
    ],
)
def test_use_process_start_time(
    aggregator,
    datadog_agent,
    mocked_openmetrics_check_factory,
    expect_first_flush,
    send_distribution_buckets,
    use_process_start_time,
    process_start_time,
    agent_start_time,
):
    """
    Test that first sample is flushed or not depending on metric type, agent and server process start times.
    """

    instance = {
        "prometheus_url": "xx",
        "metrics": ["*"],
        "namespace": "",
        "send_distribution_counts_as_monotonic": True,
        "send_distribution_buckets": send_distribution_buckets,
        "use_process_start_time": use_process_start_time,
    }

    datadog_agent.set_process_start_time(agent_start_time)

    check = mocked_openmetrics_check_factory(instance)
    test_data = _make_test_use_process_start_time_data(process_start_time)
    check.poll = mock.MagicMock(return_value=MockResponse(test_data, headers={'Content-Type': text_content_type}))

    for _ in range(0, 5):
        aggregator.reset()
        check.check(instance)

        aggregator.assert_metric(
            'go_memstats_alloc_bytes_total',
            metric_type=aggregator.MONOTONIC_COUNT,
            count=1,
            flush_first_value=expect_first_flush,
        )
        aggregator.assert_metric(
            'go_gc_duration_seconds.count',
            metric_type=aggregator.MONOTONIC_COUNT,
            count=1,
            flush_first_value=expect_first_flush,
        )

        if send_distribution_buckets:
            aggregator.assert_histogram_bucket(
                'skydns_skydns_dns_request_duration_seconds',
                None,
                None,
                None,
                True,
                None,
                None,
                count=2,
                flush_first_value=expect_first_flush,
            )
        else:
            aggregator.assert_metric(
                'skydns_skydns_dns_request_duration_seconds.count',
                metric_type=aggregator.MONOTONIC_COUNT,
                count=2,
                flush_first_value=expect_first_flush,
            )

        expect_first_flush = True


def test_refresh_bearer_token(text_data, mocked_openmetrics_check_factory):
    instance = {
        'prometheus_url': 'https://fake.endpoint:10055/metrics',
        'metrics': [{'process_virtual_memory_bytes': 'process.vm.bytes'}],
        "namespace": "default_namespace",
        "bearer_token_auth": True,
        "bearer_token_refresh_interval": 1,
    }

    with patch.object(OpenMetricsBaseCheck, 'KUBERNETES_TOKEN_PATH', os.path.join(TOKENS_PATH, 'default_token')):
        check = mocked_openmetrics_check_factory(instance)
        check.poll = mock.MagicMock(return_value=MockResponse(text_data, headers={'Content-Type': text_content_type}))
        instance = check.get_scraper_config(instance)
        assert instance['_bearer_token'] == 'my default token'
        time.sleep(1.5)
        with patch.object(OpenMetricsBaseCheck, 'KUBERNETES_TOKEN_PATH', os.path.join(TOKENS_PATH, 'custom_token')):
            check.check(instance)
            assert instance['_bearer_token'] == 'my custom token'
