# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging
import os

import math
import mock
import pytest
import requests

from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, SummaryMetricFamily, HistogramMetricFamily

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck


text_content_type = 'text/plain; version=0.0.4'


class MockResponse:
    """
    MockResponse is used to simulate the object requests.Response commonly returned by requests.get
    """

    def __init__(self, content, content_type):
        self.content = content
        self.headers = {'Content-Type': content_type}

    def iter_lines(self, **_):
        for elt in self.content.split("\n"):
            yield elt

    def close(self):
        pass


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator

    aggregator.reset()
    return aggregator


PROMETHEUS_CHECK_INSTANCE = {
    'prometheus_url': 'http://fake.endpoint:10055/metrics',
    'metrics': [{'process_virtual_memory_bytes': 'process.vm.bytes'}],
    'namespace': 'prometheus',

    # Defaults for checks that were based on PrometheusCheck
    'send_monotonic_counter': False,
    'health_service_check': True
}


@pytest.fixture
def mocked_prometheus_check():
    check = OpenMetricsBaseCheck('prometheus_check', {}, {})
    check.log = logging.getLogger('datadog-prometheus.test')
    check.log.debug = mock.MagicMock()
    return check


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
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'prometheus', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
        assert len(text_data) == 14494

    return text_data


@pytest.fixture()
def mock_get():
    text_data = None
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'prometheus', 'ksm.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': text_content_type}
        ),
    ):
        yield text_data


def test_process(text_data, mocked_prometheus_check, mocked_prometheus_scraper_config, ref_gauge):
    check = mocked_prometheus_check
    check.poll = mock.MagicMock(return_value=MockResponse(text_data, text_content_type))
    check.process_metric = mock.MagicMock()
    check.process(mocked_prometheus_scraper_config)
    check.poll.assert_called_with(mocked_prometheus_scraper_config)
    check.process_metric.assert_called_with(ref_gauge, mocked_prometheus_scraper_config, metric_transformers=None)


def test_process_metric_gauge(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, ref_gauge):
    """ Gauge ref submission """
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['_dry_run'] = False
    check.process_metric(ref_gauge, mocked_prometheus_scraper_config)

    aggregator.assert_metric('prometheus.process.vm.bytes', 54927360.0, tags=[], count=1)


def test_process_metric_filtered(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """ Metric absent from the metrics_mapper """
    filtered_gauge = GaugeMetricFamily('process_start_time_seconds', 'Start time of the process since unix epoch in seconds.')
    filtered_gauge.add_metric([], 123456789.0)
    mocked_prometheus_scraper_config['_dry_run'] = False

    check = mocked_prometheus_check
    check.process_metric(filtered_gauge, mocked_prometheus_scraper_config, metric_transformers={})
    check.log.debug.assert_called_with(
        "Unable to handle metric: process_start_time_seconds - error: No handler function named 'process_start_time_seconds' defined"
    )
    aggregator.assert_all_metrics_covered()


def test_poll_text_plain(mocked_prometheus_check, mocked_prometheus_scraper_config, text_data):
    """Tests poll using the text format"""
    check = mocked_prometheus_check
    mock_response = mock.MagicMock(
        status_code=200,
        iter_lines=lambda **kwargs: text_data.split("\n"),
        headers={'Content-Type': text_content_type})
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        response = check.poll(mocked_prometheus_scraper_config)
        messages = list(check.parse_metric_family(response, mocked_prometheus_scraper_config))
        messages.sort(key=lambda x: x.name)
        assert len(messages) == 40
        assert messages[-1].name == 'skydns_skydns_dns_response_size_bytes'


def test_submit_gauge_with_labels(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """ submitting metrics that contain labels should result in tags on the gauge call """
    ref_gauge = GaugeMetricFamily('process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'my_2nd_label'])
    ref_gauge.add_metric(['my_1st_label_value', 'my_2nd_label_value'], 54927360.0)

    check = mocked_prometheus_check
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check._submit(metric_name, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['my_1st_label:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'],
        count=1,
    )


def test_submit_gauge_with_labels_and_hostname_override(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config
):
    """ submitting metrics that contain labels should result in tags on the gauge call """
    ref_gauge = GaugeMetricFamily('process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'node'])
    ref_gauge.add_metric(['my_1st_label_value', 'foo'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['label_to_hostname'] = 'node'
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check._submit(metric_name, ref_gauge, mocked_prometheus_scraper_config)
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
    check2._submit(metric_name, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['my_1st_label:my_1st_label_value', 'node:foo'],
        hostname="foo-cluster-blue",
        count=1,
    )


def test_submit_gauge_with_labels_and_hostname_already_overridden(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config
):
    """ submitting metrics that contain labels should result in tags on the gauge call """
    ref_gauge = GaugeMetricFamily('process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'node'])
    ref_gauge.add_metric(['my_1st_label_value', 'foo'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['label_to_hostname'] = 'node'
    metric_name = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check._submit(metric_name, ref_gauge, mocked_prometheus_scraper_config, hostname='bar')
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
    ref_gauge = GaugeMetricFamily('process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'my_2nd_label'])
    ref_gauge.add_metric(['my_1st_label_value', 'my_2nd_label_value'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['custom_tags'] = ['test']
    metric = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check._submit(metric, ref_gauge, mocked_prometheus_scraper_config)
    # Call a second time to check that the labels were not added once more to the tags list and
    # avoid regression on https://github.com/DataDog/dd-agent/pull/3359
    check._submit(metric, ref_gauge, mocked_prometheus_scraper_config)

    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['test', 'my_1st_label:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'],
        count=2,
    )


def test_submit_gauge_with_custom_tags(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, ref_gauge
):
    """ Providing custom tags should add them as is on the gauge call """
    check = mocked_prometheus_check
    tags = ['env:dev', 'app:my_pretty_app']
    mocked_prometheus_scraper_config['custom_tags'] = tags
    metric = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check._submit(metric, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric('prometheus.process.vm.bytes', 54927360.0, tags=tags, count=1)


def test_submit_gauge_with_labels_mapper(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config
):
    """
    Submitting metrics that contain labels mappers should result in tags
    on the gauge call with transformed tag names
    """
    ref_gauge = GaugeMetricFamily('process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'my_2nd_label'])
    ref_gauge.add_metric(['my_1st_label_value', 'my_2nd_label_value'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['labels_mapper'] = {
        'my_1st_label': 'transformed_1st',
        'non_existent': 'should_not_matter',
        'env': 'dont_touch_custom_tags',
    }
    mocked_prometheus_scraper_config['custom_tags'] = ['env:dev', 'app:my_pretty_app']
    metric = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check._submit(metric, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['env:dev', 'app:my_pretty_app', 'transformed_1st:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'],
        count=1,
    )


def test_submit_gauge_with_exclude_labels(
    aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config
):
    """
    Submitting metrics when filtering with exclude_labels should end up with
    a filtered tags list
    """
    ref_gauge = GaugeMetricFamily('process_virtual_memory_bytes', 'Virtual memory size in bytes.', labels=['my_1st_label', 'my_2nd_label'])
    ref_gauge.add_metric(['my_1st_label_value', 'my_2nd_label_value'], 54927360.0)

    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['labels_mapper'] = {
        'my_1st_label': 'transformed_1st',
        'non_existent': 'should_not_matter',
        'env': 'dont_touch_custom_tags',
    }
    mocked_prometheus_scraper_config['custom_tags'] = ['env:dev', 'app:my_pretty_app']
    mocked_prometheus_scraper_config['exclude_labels'] = [
        'my_2nd_label',
        'whatever_else',
        'env',
    ]  # custom tags are not filtered out
    metric = mocked_prometheus_scraper_config['metrics_mapper'][ref_gauge.name]
    check._submit(metric, ref_gauge, mocked_prometheus_scraper_config)
    aggregator.assert_metric(
        'prometheus.process.vm.bytes',
        54927360.0,
        tags=['env:dev', 'app:my_pretty_app', 'transformed_1st:my_1st_label_value'],
        count=1,
    )


def test_submit_counter(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    _counter = CounterMetricFamily('my_counter', 'Random counter')
    _counter.add_metric([], 42)
    check = mocked_prometheus_check
    check._submit('custom.counter', _counter, mocked_prometheus_scraper_config)
    aggregator.assert_metric('prometheus.custom.counter', 42, tags=[], count=1)
    aggregator.assert_all_metrics_covered()


def test_submit_summary(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    _sum = SummaryMetricFamily('my_summary', 'Random summary')
    _sum.add_metric([], 5.0, 120512.0)
    _sum.add_sample("my_summary", {"quantile": "0.5"}, 24547.0)
    _sum.add_sample("my_summary", {"quantile": "0.9"}, 25763.0)
    _sum.add_sample("my_summary", {"quantile": "0.99"}, 25763.0)
    check = mocked_prometheus_check
    check._submit('custom.summary', _sum, mocked_prometheus_scraper_config)
    aggregator.assert_metric('prometheus.custom.summary.count', 5.0, tags=[], count=1)
    aggregator.assert_metric('prometheus.custom.summary.sum', 120512.0, tags=[], count=1)
    aggregator.assert_metric('prometheus.custom.summary.quantile', 24547.0, tags=['quantile:0.5'], count=1)
    aggregator.assert_metric('prometheus.custom.summary.quantile', 25763.0, tags=['quantile:0.9'], count=1)
    aggregator.assert_metric('prometheus.custom.summary.quantile', 25763.0, tags=['quantile:0.99'], count=1)
    aggregator.assert_all_metrics_covered()


def test_submit_histogram(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    _histo = HistogramMetricFamily('my_histogram', 'my_histogram')
    _histo.add_metric([], buckets=[("-Inf", 0), ("1", 1), ("3.1104e+07", 1), ("4.324e+08", 1) , ("+Inf", 3)], sum_value=3)
    check = mocked_prometheus_check
    check._submit('custom.histogram', _histo, mocked_prometheus_scraper_config)
    aggregator.assert_metric('prometheus.custom.histogram.sum', 3, tags=[], count=1)
    aggregator.assert_metric('prometheus.custom.histogram.count', 3, tags=[], count=1)
    aggregator.assert_metric('prometheus.custom.histogram.count', 1, tags=['upper_bound:1.0'], count=1)
    aggregator.assert_metric('prometheus.custom.histogram.count', 1, tags=['upper_bound:31104000.0'], count=1)
    aggregator.assert_metric('prometheus.custom.histogram.count', 1, tags=['upper_bound:432400000.0'], count=1)
    aggregator.assert_all_metrics_covered()


def test_submit_rate(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    _rate = GaugeMetricFamily('my_rate', 'Random rate')
    _rate.add_metric([], 42)
    check = mocked_prometheus_check
    check._submit('custom.rate', _rate, mocked_prometheus_scraper_config)
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
        'kube_deployment_status_replicas{deployment="kube-dns"} 2\n')

    expected_metric = GaugeMetricFamily('kube_deployment_status_replicas', 'The number of replicas per deployment.', labels=['deployment'])
    expected_metric.add_metric(['event-exporter-v0.1.7'], 1)
    expected_metric.add_metric(['heapster-v1.4.3'], 1)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    mocked_prometheus_scraper_config['_text_filter_blacklist'] = ["deployment=\"kube-dns\""]
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]

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

    expected_etcd_metric = GaugeMetricFamily('etcd_server_has_leader', 'Whether or not a leader exists. 1 is existence, 0 is not.')
    expected_etcd_metric.add_metric([], 1)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]

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

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]

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

    expected_etcd_vault_metric = HistogramMetricFamily('etcd_disk_wal_fsync_duration_seconds',
        'The latency distributions of fsync called by wal.',
        labels=['app']
    )
    expected_etcd_vault_metric.add_metric(['vault'], buckets=[
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
        ('+Inf', 4.0)
    ], sum_value=0.026131671)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_vault_metric.documentation == current_metric.documentation
    assert expected_etcd_vault_metric.name == current_metric.name
    assert expected_etcd_vault_metric.type == current_metric.type
    assert sorted(expected_etcd_vault_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])


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

    expected_etcd_metric = HistogramMetricFamily('etcd_disk_wal_fsync_duration_seconds', 'The latency distributions of fsync called by wal.')
    expected_etcd_metric.add_metric([], buckets=[
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
        ('+Inf', 4.0)
    ], sum_value=0.026131671)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]
    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])

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
        labels=['kind', 'app']
    )
    expected_etcd_metric.add_metric(['fs', 'vault'], buckets=[
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
        ('+Inf', 4.0)
    ], sum_value=0.026131671)
    expected_etcd_metric.add_metric(['fs', 'kubernetes'], buckets=[
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
        ('+Inf', 751.0)
    ], sum_value=0.3097010759999998)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]

    assert 1 == len(metrics)

    current_metric = metrics[0]
    # in metrics with more than one label
    # the labels don't always get parsed in a deterministic order
    # deconstruct the metric to ensure it's equal
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])


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

    expected_etcd_metric = SummaryMetricFamily('http_response_size_bytes', 'The HTTP response sizes in bytes.', labels=["handler"])
    expected_etcd_metric.add_metric(["prometheus"], 5.0, 120512.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"handler":"prometheus", "quantile": "0.5"}, 24547.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"handler":"prometheus", "quantile": "0.9"}, 25763.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"handler":"prometheus", "quantile": "0.99"}, 25763.0)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])

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

    expected_etcd_metric = SummaryMetricFamily('http_response_size_bytes', 'The HTTP response sizes in bytes.', labels=["handler"])
    expected_etcd_metric.add_metric(["prometheus"], 5.0, 120512.0)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])


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

    expected_etcd_metric = SummaryMetricFamily('http_response_size_bytes', 'The HTTP response sizes in bytes.', labels=["from","handler"])
    expected_etcd_metric.add_metric(["internet","prometheus"], 5.0, 120512.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"from":"internet", "handler":"prometheus", "quantile": "0.5"}, 24547.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"from":"internet", "handler":"prometheus", "quantile": "0.9"}, 25763.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"from":"internet", "handler":"prometheus", "quantile": "0.99"}, 25763.0)
    expected_etcd_metric.add_metric(["cluster","prometheus"], 4.0, 94913.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"from":"cluster", "handler":"prometheus", "quantile": "0.5"}, 24615.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"from":"cluster", "handler":"prometheus", "quantile": "0.9"}, 24627.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"from":"cluster", "handler":"prometheus", "quantile": "0.99"}, 24627.0)

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]

    assert 1 == len(metrics)

    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    assert sorted(expected_etcd_metric.samples, key=lambda i: i[0]) == sorted(current_metric.samples, key=lambda i: i[0])

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

    expected_etcd_metric = SummaryMetricFamily('http_response_size_bytes', 'The HTTP response sizes in bytes.', labels=["handler"])
    expected_etcd_metric.add_metric(["prometheus"], 0.0, 0.0)
    expected_etcd_metric.add_sample("http_response_size_bytes", {"handler":"prometheus", "quantile": "0.5"}, float('nan'))
    expected_etcd_metric.add_sample("http_response_size_bytes", {"handler":"prometheus", "quantile": "0.9"}, float('nan'))
    expected_etcd_metric.add_sample("http_response_size_bytes", {"handler":"prometheus", "quantile": "0.99"}, float('nan'))

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, text_content_type)
    check = p_check
    metrics = [k for k in check.parse_metric_family(response, mocked_prometheus_scraper_config)]
    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric.documentation == current_metric.documentation
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    # As the NaN value isn't supported when we are calling assertEqual
    assert math.isnan(current_metric.samples[0][2])
    assert math.isnan(current_metric.samples[1][2])
    assert math.isnan(current_metric.samples[2][2])

def test_label_joins(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """ Tests label join on text format """
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node', 'pod_ip']},
        'kube_deployment_labels': {
            'label_to_match': 'deployment',
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
    aggregator.assert_metric('ksm.pod.ready', 1.0,
        tags=['pod:event-exporter-v0.1.7-958884745-qgnbw',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.14'], count=1)
    aggregator.assert_metric('ksm.pod.ready', 1.0,
        tags=['pod:fluentd-gcp-v2.0.9-6dj58',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.132.0.7'], count=1)
    aggregator.assert_metric('ksm.pod.ready', 1.0,
        tags=['pod:fluentd-gcp-v2.0.9-z348z',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.132.0.14'], count=1)
    aggregator.assert_metric('ksm.pod.ready', 1.0,
        tags=['pod:heapster-v1.4.3-2027615481-lmjm5',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.32.5.7'], count=1)
    aggregator.assert_metric('ksm.pod.ready', 1.0,
        tags=['pod:kube-dns-3092422022-lvrmx',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.10'], count=1)
    aggregator.assert_metric('ksm.pod.ready', 1.0,
        tags=['pod:kube-dns-3092422022-x0tjx',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.9'], count=1)
    aggregator.assert_metric('ksm.pod.ready', 1.0,
        tags=['pod:kube-dns-autoscaler-97162954-mf6d3',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.32.5.6'], count=1)
    aggregator.assert_metric('ksm.pod.ready', 1.0,
        tags=['pod:kube-proxy-gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.132.0.7'], count=1)
    aggregator.assert_metric('ksm.pod.scheduled', 1.0,
        tags=['pod:ungaged-panther-kube-state-metrics-3918010230-64xwc',
            'namespace:default',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.32.5.45'], count=1)
    aggregator.assert_metric('ksm.pod.scheduled', 1.0,
        tags=['pod:event-exporter-v0.1.7-958884745-qgnbw',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.14'], count=1)
    aggregator.assert_metric('ksm.pod.scheduled', 1.0,
        tags=['pod:fluentd-gcp-v2.0.9-6dj58',
        'namespace:kube-system',
        'condition:true',
        'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
        'pod_ip:11.132.0.7'], count=1)
    aggregator.assert_metric('ksm.pod.scheduled', 1.0,
        tags=['pod:fluentd-gcp-v2.0.9-z348z',
        'namespace:kube-system',
        'condition:true',
        'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
        'pod_ip:11.132.0.14'], count=1)
    aggregator.assert_metric('ksm.pod.scheduled', 1.0,
        tags=['pod:heapster-v1.4.3-2027615481-lmjm5',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
            'pod_ip:11.32.5.7'], count=1)
    aggregator.assert_metric('ksm.pod.scheduled', 1.0,
        tags=['pod:kube-dns-3092422022-lvrmx',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.10'], count=1)
    aggregator.assert_metric('ksm.pod.scheduled', 1.0,
        tags=['pod:kube-dns-3092422022-x0tjx',
            'namespace:kube-system',
            'condition:true',
            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
            'pod_ip:11.32.3.9'], count=1)
    aggregator.assert_metric('ksm.deploy.replicas.available', 1.0,
        tags=['namespace:kube-system',
            'deployment:event-exporter-v0.1.7',
            'label_k8s_app:event-exporter',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_kubernetes_io_cluster_service:true'], count=1)
    aggregator.assert_metric('ksm.deploy.replicas.available', 1.0,
        tags=['namespace:kube-system',
            'deployment:heapster-v1.4.3',
            'label_k8s_app:heapster',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_kubernetes_io_cluster_service:true'], count=1)
    aggregator.assert_metric('ksm.deploy.replicas.available', 2.0,
        tags=['namespace:kube-system',
            'deployment:kube-dns',
            'label_kubernetes_io_cluster_service:true',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_k8s_app:kube-dns'], count=1)
    aggregator.assert_metric('ksm.deploy.replicas.available', 1.0,
        tags=['namespace:kube-system',
            'deployment:kube-dns-autoscaler',
            'label_kubernetes_io_cluster_service:true',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_k8s_app:kube-dns-autoscaler'], count=1)
    aggregator.assert_metric('ksm.deploy.replicas.available', 1.0,
        tags=['namespace:kube-system',
            'deployment:kubernetes-dashboard',
            'label_kubernetes_io_cluster_service:true',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_k8s_app:kubernetes-dashboard'], count=1)
    aggregator.assert_metric('ksm.deploy.replicas.available', 1.0,
        tags=['namespace:kube-system',
            'deployment:l7-default-backend',
            'label_k8s_app:glbc',
            'label_addonmanager_kubernetes_io_mode:Reconcile',
            'label_kubernetes_io_cluster_service:true'], count=1)
    aggregator.assert_metric('ksm.deploy.replicas.available', 1.0,
        tags=['namespace:kube-system',
            'deployment:tiller-deploy'], count=1)
    aggregator.assert_metric('ksm.deploy.replicas.available', 1.0,
        tags=['namespace:default',
            'deployment:ungaged-panther-kube-state-metrics'], count=1)

def test_label_joins_gc(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """ Tests label join GC on text format """
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    mocked_prometheus_scraper_config['label_joins'] = {
        'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node', 'pod_ip']}
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
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': text_content_type}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check.process(mocked_prometheus_scraper_config)
        assert 'dd-agent-1337' in mocked_prometheus_scraper_config['_label_mapping']['pod']
        assert 'dd-agent-62bgh' not in mocked_prometheus_scraper_config['_label_mapping']['pod']
        assert 15 == len(mocked_prometheus_scraper_config['_label_mapping']['pod'])

def test_label_joins_missconfigured(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """ Tests label join missconfigured label is ignored """
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
    """ Tests label join on non existing matching label is ignored """
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

def test_label_join_metric_not_existing(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config, mock_get):
    """ Tests label join on non existing metric is ignored """
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
    """ Tests label join and hostname override on a metric """
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


def test_health_service_check_ok(mock_get, aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """ Tests endpoint health service check OK """
    check = mocked_prometheus_check

    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    check.process(mocked_prometheus_scraper_config)

    aggregator.assert_service_check(
        'ksm.prometheus.health', status=OpenMetricsBaseCheck.OK, tags=['endpoint:http://fake.endpoint:10055/metrics'], count=1
    )


def test_health_service_check_failing(aggregator, mocked_prometheus_check, mocked_prometheus_scraper_config):
    """ Tests endpoint health service check failing """
    check = mocked_prometheus_check

    mocked_prometheus_scraper_config['namespace'] = 'ksm'
    with pytest.raises(requests.ConnectionError):
        check.process(mocked_prometheus_scraper_config)
    aggregator.assert_service_check(
        'ksm.prometheus.health', status=OpenMetricsBaseCheck.CRITICAL, tags=["endpoint:http://fake.endpoint:10055/metrics"], count=1
    )

def test_text_filter_input(mocked_prometheus_check, mocked_prometheus_scraper_config):
    check = mocked_prometheus_check
    mocked_prometheus_scraper_config['_text_filter_blacklist'] = ["string1", "string2"]

    lines_in = [
        "line with string3",
        "line with string1",
        "line with string2",
        "line with string1 and string2",
        "line with string"
    ]
    expected_out = [
        "line with string3",
        "line with string"
    ]

    filtered = [x for x in check._text_filter_input(lines_in, mocked_prometheus_scraper_config)]
    assert filtered == expected_out
