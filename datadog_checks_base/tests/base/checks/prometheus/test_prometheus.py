# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2016-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging
import os
from collections import OrderedDict

import mock
import pytest
import requests
from six import iteritems, iterkeys
from six.moves import range

from datadog_checks.checks.prometheus import PrometheusCheck, UnknownFormatError
from datadog_checks.utils.prometheus import metrics_pb2, parse_metric_family

protobuf_content_type = 'application/vnd.google.protobuf; proto=io.prometheus.client.MetricFamily; encoding=delimited'


FIXTURES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'fixtures', 'prometheus'))


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


class SortedTagsPrometheusCheck(PrometheusCheck):
    """
    Tags are not sorted in a deterministic manner. There is no need to sort them normally.
    However, in order to ensure that the correct tags are submitted, the tags will need to be sorted
    This is a skeleton class to do that
    """

    def _finalize_tags_to_submit(self, _tags, metric_name, val, metric, custom_tags=None, hostname=None):
        """
        Format the finalized tags
        This is generally a noop, but it can be used to hook into _submit_gauge and change the tags before sending
        """
        return sorted(_tags)


@pytest.fixture
def mocked_prometheus_check():
    check = PrometheusCheck('prometheus_check', {}, {}, {})
    check.gauge = mock.MagicMock()
    check.rate = mock.MagicMock()
    check.log = logging.getLogger('datadog-prometheus.test')
    check.log.debug = mock.MagicMock()
    check.metrics_mapper = {'process_virtual_memory_bytes': 'process.vm.bytes'}
    check.NAMESPACE = 'prometheus'

    return check


@pytest.fixture
def p_check():
    return PrometheusCheck('prometheus_check', {}, {}, {})


@pytest.fixture
def sorted_tags_check():
    return SortedTagsPrometheusCheck('prometheus_check', {}, {}, {})


@pytest.fixture
def ref_gauge():
    ref_gauge = metrics_pb2.MetricFamily()
    ref_gauge.name = 'process_virtual_memory_bytes'
    ref_gauge.help = 'Virtual memory size in bytes.'
    ref_gauge.type = 1  # GAUGE
    _m = ref_gauge.metric.add()
    _m.gauge.value = 39211008.0

    return ref_gauge


@pytest.fixture
def bin_data():
    f_name = os.path.join(FIXTURES_PATH, 'protobuf.bin')
    with open(f_name, 'rb') as f:
        bin_data = f.read()
        assert len(bin_data) == 51855

    return bin_data


@pytest.fixture
def text_data():
    # Loading test text data
    f_name = os.path.abspath(os.path.join(FIXTURES_PATH, 'metrics.txt'))
    with open(f_name, 'r') as f:
        text_data = f.read()
        assert len(text_data) == 14494

    return text_data


def test_parse_metric_family():
    f_name = os.path.join(FIXTURES_PATH, 'protobuf.bin')
    with open(f_name, 'rb') as f:
        data = f.read()
        assert len(data) == 51855
        messages = list(parse_metric_family(data))
        assert len(messages) == 61
        assert messages[-1].name == 'process_virtual_memory_bytes'


def test_check(mocked_prometheus_check):
    """Should not be implemented as it is the mother class"""
    with pytest.raises(NotImplementedError):
        mocked_prometheus_check.check(None)


def test_parse_metric_family_protobuf(bin_data, mocked_prometheus_check):
    response = MockResponse(bin_data, protobuf_content_type)
    check = mocked_prometheus_check

    messages = list(check.parse_metric_family(response))

    assert len(messages) == 61
    assert messages[-1].name == 'process_virtual_memory_bytes'

    # check type overriding is working
    # original type:
    assert messages[1].name == 'go_goroutines'
    assert messages[1].type == 1  # gauge

    # override the type:
    check.type_overrides = {"go_goroutines": "summary"}

    response = MockResponse(bin_data, protobuf_content_type)

    messages = list(check.parse_metric_family(response))

    assert len(messages) == 61
    assert messages[1].name == 'go_goroutines'
    assert messages[1].type == 2  # summary


def test_parse_metric_family_text(text_data, mocked_prometheus_check):
    """Test the high level method for loading metrics from text format"""
    check = mocked_prometheus_check

    response = MockResponse(text_data, 'text/plain; version=0.0.4')

    messages = list(check.parse_metric_family(response))
    # total metrics are 41 but one is typeless and we expect it not to be
    # parsed...
    assert len(messages) == 40
    # ...unless the check ovverrides the type manually
    check.type_overrides = {"go_goroutines": "gauge"}
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    messages = list(check.parse_metric_family(response))
    assert len(messages) == 41
    # Tests correct parsing of counters
    _counter = metrics_pb2.MetricFamily()
    _counter.name = 'skydns_skydns_dns_cachemiss_count_total'
    _counter.help = 'Counter of DNS requests that result in a cache miss.'
    _counter.type = 0  # COUNTER
    _c = _counter.metric.add()
    _c.counter.value = 1359194.0
    _lc = _c.label.add()
    _lc.name = 'cache'
    _lc.value = 'response'
    assert _counter in messages
    # Tests correct parsing of gauges
    _gauge = metrics_pb2.MetricFamily()
    _gauge.name = 'go_memstats_heap_alloc_bytes'
    _gauge.help = 'Number of heap bytes allocated and still in use.'
    _gauge.type = 1  # GAUGE
    _gauge.metric.add().gauge.value = 6396288.0
    assert _gauge in messages
    # Tests correct parsing of summaries
    _summary = metrics_pb2.MetricFamily()
    _summary.name = 'http_response_size_bytes'
    _summary.help = 'The HTTP response sizes in bytes.'
    _summary.type = 2  # SUMMARY
    _sm = _summary.metric.add()
    _lsm = _sm.label.add()
    _lsm.name = 'handler'
    _lsm.value = 'prometheus'
    _sm.summary.sample_count = 25
    _sm.summary.sample_sum = 147728.0
    _sq1 = _sm.summary.quantile.add()
    _sq1.quantile = 0.5
    _sq1.value = 21470.0
    _sq2 = _sm.summary.quantile.add()
    _sq2.quantile = 0.9
    _sq2.value = 21470.0
    _sq3 = _sm.summary.quantile.add()
    _sq3.quantile = 0.99
    _sq3.value = 21470.0
    assert _summary in messages
    # Tests correct parsing of histograms
    _histo = metrics_pb2.MetricFamily()
    _histo.name = 'skydns_skydns_dns_response_size_bytes'
    _histo.help = 'Size of the returns response in bytes.'
    _histo.type = 4  # HISTOGRAM
    _sample_data = [
        {
            'ct': 1359194,
            'sum': 199427281.0,
            'lbl': {'system': 'auth'},
            'buckets': {
                0.0: 0,
                512.0: 1359194,
                1024.0: 1359194,
                1500.0: 1359194,
                2048.0: 1359194,
                float('+Inf'): 1359194,
            },
        },
        {
            'ct': 520924,
            'sum': 41527128.0,
            'lbl': {'system': 'recursive'},
            'buckets': {0.0: 0, 512.0: 520924, 1024.0: 520924, 1500.0: 520924, 2048.0: 520924, float('+Inf'): 520924},
        },
        {
            'ct': 67648,
            'sum': 6075182.0,
            'lbl': {'system': 'reverse'},
            'buckets': {0.0: 0, 512.0: 67648, 1024.0: 67648, 1500.0: 67648, 2048.0: 67648, float('+Inf'): 67648},
        },
    ]
    for _data in _sample_data:
        _h = _histo.metric.add()
        _h.histogram.sample_count = _data['ct']
        _h.histogram.sample_sum = _data['sum']
        for k, v in list(iteritems(_data['lbl'])):
            _lh = _h.label.add()
            _lh.name = k
            _lh.value = v
        for _b in sorted(iterkeys(_data['buckets'])):
            _subh = _h.histogram.bucket.add()
            _subh.upper_bound = _b
            _subh.cumulative_count = _data['buckets'][_b]
    assert _histo in messages


def test_parse_metric_family_unsupported(bin_data, mocked_prometheus_check):
    check = mocked_prometheus_check
    with pytest.raises(UnknownFormatError):
        response = MockResponse(bin_data, 'application/json')
        list(check.parse_metric_family(response))


def test_process(bin_data, mocked_prometheus_check, ref_gauge):
    endpoint = "http://fake.endpoint:10055/metrics"
    check = mocked_prometheus_check

    check.poll = mock.MagicMock(return_value=MockResponse(bin_data, protobuf_content_type))
    check.process_metric = mock.MagicMock()
    check.process(endpoint, instance=None)
    check.poll.assert_called_with(endpoint, instance={})
    check.process_metric.assert_called_with(ref_gauge, instance=None)


def test_process_send_histograms_buckets(bin_data, mocked_prometheus_check, ref_gauge):
    """Checks that the send_histograms_buckets parameter is passed along"""
    endpoint = "http://fake.endpoint:10055/metrics"
    check = mocked_prometheus_check
    check.poll = mock.MagicMock(return_value=MockResponse(bin_data, protobuf_content_type))
    check.process_metric = mock.MagicMock()
    check.process(endpoint, send_histograms_buckets=False, instance=None)
    check.poll.assert_called_with(endpoint, instance={})
    check.process_metric.assert_called_with(ref_gauge, instance=None, send_histograms_buckets=False)


def test_process_send_monotonic_counter(bin_data, mocked_prometheus_check, ref_gauge):
    """Checks that the send_monotonic_counter parameter is passed along"""
    endpoint = "http://fake.endpoint:10055/metrics"
    check = mocked_prometheus_check
    check.poll = mock.MagicMock(return_value=MockResponse(bin_data, protobuf_content_type))
    check.process_metric = mock.MagicMock()
    check.process(endpoint, send_monotonic_counter=False, instance=None)
    check.poll.assert_called_with(endpoint, instance={})
    check.process_metric.assert_called_with(ref_gauge, instance=None, send_monotonic_counter=False)


def test_process_instance_with_tags(bin_data, mocked_prometheus_check, ref_gauge):
    """Checks that an instances with tags passes them as custom tag"""
    endpoint = "http://fake.endpoint:10055/metrics"
    check = mocked_prometheus_check
    check.poll = mock.MagicMock(return_value=MockResponse(bin_data, protobuf_content_type))
    check.process_metric = mock.MagicMock()
    instance = {'endpoint': 'IgnoreMe', 'tags': ['tag1:tagValue1', 'tag2:tagValue2']}
    check.process(endpoint, instance=instance)
    check.poll.assert_called_with(endpoint, instance=instance)
    check.process_metric.assert_called_with(
        ref_gauge, custom_tags=['tag1:tagValue1', 'tag2:tagValue2'], instance=instance
    )


def test_process_metric_gauge(mocked_prometheus_check, ref_gauge):
    """Gauge ref submission"""
    check = mocked_prometheus_check
    check._dry_run = False
    check.process_metric(ref_gauge)
    check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0, [], hostname=None)


def test_process_metric_filtered(mocked_prometheus_check):
    """Metric absent from the metrics_mapper"""
    filtered_gauge = metrics_pb2.MetricFamily()
    filtered_gauge.name = "process_start_time_seconds"
    filtered_gauge.help = "Start time of the process since unix epoch in seconds."
    filtered_gauge.type = 1  # GAUGE
    _m = filtered_gauge.metric.add()
    _m.gauge.value = 39211008.0
    check = mocked_prometheus_check
    check._dry_run = False
    check.process_metric(filtered_gauge)
    check.log.debug.assert_called_with(
        "Unable to handle metric: %s - error: %s", "process_start_time_seconds", mock.ANY
    )
    check.gauge.assert_not_called()


def test_poll_protobuf(mocked_prometheus_check, bin_data):
    """Tests poll using the protobuf format"""
    check = mocked_prometheus_check
    mock_response = mock.MagicMock(status_code=200, content=bin_data, headers={'Content-Type': protobuf_content_type})
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        response = check.poll("http://fake.endpoint:10055/metrics")
        messages = list(check.parse_metric_family(response))
        assert len(messages) == 61
        assert messages[-1].name == 'process_virtual_memory_bytes'


def test_poll_text_plain(mocked_prometheus_check, text_data):
    """Tests poll using the text format"""
    check = mocked_prometheus_check
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        response = check.poll("http://fake.endpoint:10055/metrics")
        messages = list(check.parse_metric_family(response))
        messages.sort(key=lambda x: x.name)
        assert len(messages) == 40
        assert messages[-1].name == 'skydns_skydns_dns_response_size_bytes'


def test_submit_gauge_with_labels(mocked_prometheus_check, ref_gauge):
    """submitting metrics that contain labels should result in tags on the gauge call"""
    _l1 = ref_gauge.metric[0].label.add()
    _l1.name = 'my_1st_label'
    _l1.value = 'my_1st_label_value'
    _l2 = ref_gauge.metric[0].label.add()
    _l2.name = 'my_2nd_label'
    _l2.value = 'my_2nd_label_value'
    _l3 = ref_gauge.metric[0].label.add()
    _l3.name = 'labél'
    _l3.value = 'my_labél_value'
    _l4 = ref_gauge.metric[0].label.add()
    _l4.name = 'labél_mix'
    _l4.value = u'my_labél_value🇫🇷🇪🇸🇺🇸'
    _l5 = ref_gauge.metric[0].label.add()
    _l5.name = u'labél_unicode'
    _l5.value = u'my_labél_value'
    check = mocked_prometheus_check
    check._submit(check.metrics_mapper[ref_gauge.name], ref_gauge)
    check.gauge.assert_called_with(
        'prometheus.process.vm.bytes',
        39211008.0,
        [
            'my_1st_label:my_1st_label_value',
            'my_2nd_label:my_2nd_label_value',
            'labél:my_labél_value',
            'labél_mix:my_labél_value🇫🇷🇪🇸🇺🇸',
            'labél_unicode:my_labél_value',
        ],
        hostname=None,
    )


def test_submit_gauge_with_labels_and_hostname_override(mocked_prometheus_check, ref_gauge):
    """submitting metrics that contain labels should result in tags on the gauge call"""
    _l1 = ref_gauge.metric[0].label.add()
    _l1.name = 'my_1st_label'
    _l1.value = 'my_1st_label_value'
    _l2 = ref_gauge.metric[0].label.add()
    _l2.name = 'node'
    _l2.value = 'foo'
    check = mocked_prometheus_check
    check.label_to_hostname = 'node'
    check._submit(check.metrics_mapper[ref_gauge.name], ref_gauge)
    check.gauge.assert_called_with(
        'prometheus.process.vm.bytes', 39211008.0, ['my_1st_label:my_1st_label_value', 'node:foo'], hostname="foo"
    )
    # also test with a hostname suffix
    check2 = mocked_prometheus_check
    check2.label_to_hostname = 'node'
    check2.label_to_hostname_suffix = '-cluster-blue'
    check2._submit(check2.metrics_mapper[ref_gauge.name], ref_gauge)
    check2.gauge.assert_called_with(
        'prometheus.process.vm.bytes',
        39211008.0,
        ['my_1st_label:my_1st_label_value', 'node:foo'],
        hostname="foo-cluster-blue",
    )


def test_submit_gauge_with_labels_and_hostname_already_overridden(mocked_prometheus_check, ref_gauge):
    """submitting metrics that contain labels should result in tags on the gauge call"""
    _l1 = ref_gauge.metric[0].label.add()
    _l1.name = 'my_1st_label'
    _l1.value = 'my_1st_label_value'
    _l2 = ref_gauge.metric[0].label.add()
    _l2.name = 'node'
    _l2.value = 'foo'
    check = mocked_prometheus_check
    check.label_to_hostname = 'node'
    check._submit(check.metrics_mapper[ref_gauge.name], ref_gauge, hostname="bar")
    check.gauge.assert_called_with(
        'prometheus.process.vm.bytes', 39211008.0, ['my_1st_label:my_1st_label_value', 'node:foo'], hostname="bar"
    )


def test_labels_not_added_as_tag_once_for_each_metric(mocked_prometheus_check, ref_gauge):
    _l1 = ref_gauge.metric[0].label.add()
    _l1.name = 'my_1st_label'
    _l1.value = 'my_1st_label_value'
    _l2 = ref_gauge.metric[0].label.add()
    _l2.name = 'my_2nd_label'
    _l2.value = 'my_2nd_label_value'
    tags = ['test']
    check = mocked_prometheus_check
    check._submit(check.metrics_mapper[ref_gauge.name], ref_gauge, custom_tags=tags)
    # Call a second time to check that the labels were not added once more to the tags list and
    # avoid regression on https://github.com/DataDog/dd-agent/pull/3359
    check._submit(check.metrics_mapper[ref_gauge.name], ref_gauge, custom_tags=tags)
    check.gauge.assert_called_with(
        'prometheus.process.vm.bytes',
        39211008.0,
        ['test', 'my_1st_label:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'],
        hostname=None,
    )


def test_submit_gauge_with_custom_tags(mocked_prometheus_check, ref_gauge):
    """Providing custom tags should add them as is on the gauge call"""
    tags = ['env:dev', 'app:my_pretty_app']
    check = mocked_prometheus_check
    check._submit(check.metrics_mapper[ref_gauge.name], ref_gauge, custom_tags=tags)
    check.gauge.assert_called_with(
        'prometheus.process.vm.bytes', 39211008.0, ['env:dev', 'app:my_pretty_app'], hostname=None
    )


def test_submit_gauge_with_labels_mapper(mocked_prometheus_check, ref_gauge):
    """
    Submitting metrics that contain labels mappers should result in tags
    on the gauge call with transformed tag names
    """
    _l1 = ref_gauge.metric[0].label.add()
    _l1.name = 'my_1st_label'
    _l1.value = 'my_1st_label_value'
    _l2 = ref_gauge.metric[0].label.add()
    _l2.name = 'my_2nd_label'
    _l2.value = 'my_2nd_label_value'
    check = mocked_prometheus_check
    check.labels_mapper = {
        'my_1st_label': 'transformed_1st',
        'non_existent': 'should_not_matter',
        'env': 'dont_touch_custom_tags',
    }

    tags = ['env:dev', 'app:my_pretty_app']
    check._submit(check.metrics_mapper[ref_gauge.name], ref_gauge, custom_tags=tags)
    check.gauge.assert_called_with(
        'prometheus.process.vm.bytes',
        39211008.0,
        ['env:dev', 'app:my_pretty_app', 'transformed_1st:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'],
        hostname=None,
    )


def test_submit_gauge_with_exclude_labels(mocked_prometheus_check, ref_gauge):
    """
    Submitting metrics when filtering with exclude_labels should end up with
    a filtered tags list
    """
    _l1 = ref_gauge.metric[0].label.add()
    _l1.name = 'my_1st_label'
    _l1.value = 'my_1st_label_value'
    _l2 = ref_gauge.metric[0].label.add()
    _l2.name = 'my_2nd_label'
    _l2.value = 'my_2nd_label_value'
    check = mocked_prometheus_check
    check.labels_mapper = {
        'my_1st_label': 'transformed_1st',
        'non_existent': 'should_not_matter',
        'env': 'dont_touch_custom_tags',
    }
    tags = ['env:dev', 'app:my_pretty_app']
    check.exclude_labels = ['my_2nd_label', 'whatever_else', 'env']  # custom tags are not filtered out
    check._submit(check.metrics_mapper[ref_gauge.name], ref_gauge, custom_tags=tags)
    check.gauge.assert_called_with(
        'prometheus.process.vm.bytes',
        39211008.0,
        ['env:dev', 'app:my_pretty_app', 'transformed_1st:my_1st_label_value'],
        hostname=None,
    )


def test_submit_counter(mocked_prometheus_check):
    _counter = metrics_pb2.MetricFamily()
    _counter.name = 'my_counter'
    _counter.help = 'Random counter'
    _counter.type = 0  # COUNTER
    _met = _counter.metric.add()
    _met.counter.value = 42
    check = mocked_prometheus_check
    check._submit('custom.counter', _counter)
    check.gauge.assert_called_with('prometheus.custom.counter', 42, [], hostname=None)


def test_submits_summary(mocked_prometheus_check):
    _sum = metrics_pb2.MetricFamily()
    _sum.name = 'my_summary'
    _sum.help = 'Random summary'
    _sum.type = 2  # SUMMARY
    _met = _sum.metric.add()
    _met.summary.sample_count = 42
    _met.summary.sample_sum = 3.14
    _q1 = _met.summary.quantile.add()
    _q1.quantile = 10.0
    _q1.value = 3
    _q2 = _met.summary.quantile.add()
    _q2.quantile = 4.0
    _q2.value = 5
    check = mocked_prometheus_check
    check._submit('custom.summary', _sum)
    check.gauge.assert_has_calls(
        [
            mock.call('prometheus.custom.summary.count', 42, [], hostname=None),
            mock.call('prometheus.custom.summary.sum', 3.14, [], hostname=None),
            mock.call('prometheus.custom.summary.quantile', 3, ['quantile:10.0'], hostname=None),
            mock.call('prometheus.custom.summary.quantile', 5, ['quantile:4.0'], hostname=None),
        ]
    )


def test_submit_histogram(mocked_prometheus_check):
    _histo = metrics_pb2.MetricFamily()
    _histo.name = 'my_histogram'
    _histo.help = 'Random histogram'
    _histo.type = 4  # HISTOGRAM
    _met = _histo.metric.add()
    _met.histogram.sample_count = 42
    _met.histogram.sample_sum = 3.14
    _b1 = _met.histogram.bucket.add()
    _b1.upper_bound = 12.7
    _b1.cumulative_count = 33
    _b2 = _met.histogram.bucket.add()
    _b2.upper_bound = 18.2
    _b2.cumulative_count = 666
    check = mocked_prometheus_check
    check._submit('custom.histogram', _histo)
    check.gauge.assert_has_calls(
        [
            mock.call('prometheus.custom.histogram.count', 42, ['upper_bound:none'], hostname=None),
            mock.call('prometheus.custom.histogram.sum', 3.14, [], hostname=None),
            mock.call('prometheus.custom.histogram.count', 33, ['upper_bound:12.7'], hostname=None),
            mock.call('prometheus.custom.histogram.count', 666, ['upper_bound:18.2'], hostname=None),
        ]
    )


def test_submit_rate(mocked_prometheus_check):
    _rate = metrics_pb2.MetricFamily()
    _rate.name = 'my_rate'
    _rate.help = 'Random rate'
    _rate.type = 1  # GAUGE
    _met = _rate.metric.add()
    _met.gauge.value = 42
    check = mocked_prometheus_check
    check.rate_metrics = ["my_rate"]
    check._submit('custom.rate', _rate)
    check.rate.assert_called_with('prometheus.custom.rate', 42, [], hostname=None)


def test_filter_sample_on_gauge(p_check):
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

    expected_metric = metrics_pb2.MetricFamily()
    expected_metric.help = "The number of replicas per deployment."
    expected_metric.name = "kube_deployment_status_replicas"
    expected_metric.type = 1

    gauge1 = expected_metric.metric.add()
    gauge1.gauge.value = 1
    label1 = gauge1.label.add()
    label1.name = "deployment"
    label1.value = "event-exporter-v0.1.7"

    gauge2 = expected_metric.metric.add()
    gauge2.gauge.value = 1
    label2 = gauge2.label.add()
    label2.name = "deployment"
    label2.value = "heapster-v1.4.3"

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    check = p_check
    check._text_filter_blacklist = ["deployment=\"kube-dns\""]
    metrics = [k for k in check.parse_metric_family(response)]

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_metric == current_metric


def test_parse_one_gauge(p_check):
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

    expected_etcd_metric = metrics_pb2.MetricFamily()
    expected_etcd_metric.help = "Whether or not a leader exists. 1 is existence, 0 is not."
    expected_etcd_metric.name = "etcd_server_has_leader"
    expected_etcd_metric.type = 1
    expected_etcd_metric.metric.add().gauge.value = 1

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    check = p_check
    metrics = [k for k in check.parse_metric_family(response)]

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric == current_metric

    # Remove the old metric and add a new one with a different value
    expected_etcd_metric.metric.pop()
    expected_etcd_metric.metric.add().gauge.value = 0
    assert expected_etcd_metric != current_metric

    # Re-add the expected value but as different type: it should works
    expected_etcd_metric.metric.pop()
    expected_etcd_metric.metric.add().gauge.value = 1.0
    assert expected_etcd_metric == current_metric


def test_parse_one_counter(p_check):
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

    expected_etcd_metric = metrics_pb2.MetricFamily()
    expected_etcd_metric.help = "Total number of mallocs."
    expected_etcd_metric.name = "go_memstats_mallocs_total"
    expected_etcd_metric.type = 0
    expected_etcd_metric.metric.add().counter.value = 18713

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    check = p_check
    metrics = [k for k in check.parse_metric_family(response)]

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric == current_metric

    # Remove the old metric and add a new one with a different value
    expected_etcd_metric.metric.pop()
    expected_etcd_metric.metric.add().counter.value = 18714
    assert expected_etcd_metric != current_metric


def test_parse_one_histograms_with_label(p_check):
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

    expected_etcd_vault_metric = metrics_pb2.MetricFamily()
    expected_etcd_vault_metric.help = "The latency distributions of fsync called by wal."
    expected_etcd_vault_metric.name = "etcd_disk_wal_fsync_duration_seconds"
    expected_etcd_vault_metric.type = 4

    histogram_metric = expected_etcd_vault_metric.metric.add()

    # Label for app vault
    summary_label = histogram_metric.label.add()
    summary_label.name, summary_label.value = "app", "vault"

    for upper_bound, cumulative_count in [
        (0.001, 2),
        (0.002, 2),
        (0.004, 2),
        (0.008, 2),
        (0.016, 4),
        (0.032, 4),
        (0.064, 4),
        (0.128, 4),
        (0.256, 4),
        (0.512, 4),
        (1.024, 4),
        (2.048, 4),
        (4.096, 4),
        (8.192, 4),
        (float('inf'), 4),
    ]:
        bucket = histogram_metric.histogram.bucket.add()
        bucket.upper_bound = upper_bound
        bucket.cumulative_count = cumulative_count

    # Root histogram sample
    histogram_metric.histogram.sample_count = 4
    histogram_metric.histogram.sample_sum = 0.026131671

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    check = p_check
    metrics = [k for k in check.parse_metric_family(response)]

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_vault_metric == current_metric


def test_parse_one_histogram(p_check):
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

    expected_etcd_metric = metrics_pb2.MetricFamily()
    expected_etcd_metric.help = "The latency distributions of fsync called by wal."
    expected_etcd_metric.name = "etcd_disk_wal_fsync_duration_seconds"
    expected_etcd_metric.type = 4

    histogram_metric = expected_etcd_metric.metric.add()
    for upper_bound, cumulative_count in [
        (0.001, 2),
        (0.002, 2),
        (0.004, 2),
        (0.008, 2),
        (0.016, 4),
        (0.032, 4),
        (0.064, 4),
        (0.128, 4),
        (0.256, 4),
        (0.512, 4),
        (1.024, 4),
        (2.048, 4),
        (4.096, 4),
        (8.192, 4),
        (float('inf'), 4),
    ]:
        bucket = histogram_metric.histogram.bucket.add()
        bucket.upper_bound = upper_bound
        bucket.cumulative_count = cumulative_count

    # Root histogram sample
    histogram_metric.histogram.sample_count = 4
    histogram_metric.histogram.sample_sum = 0.026131671

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    check = p_check
    metrics = [k for k in check.parse_metric_family(response)]

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric == current_metric


def test_parse_two_histograms_with_label(p_check):
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

    expected_etcd_metric = metrics_pb2.MetricFamily()
    expected_etcd_metric.help = "The latency distributions of fsync called by wal."
    expected_etcd_metric.name = "etcd_disk_wal_fsync_duration_seconds"
    expected_etcd_metric.type = 4

    # Vault
    histogram_metric = expected_etcd_metric.metric.add()

    # Label for app vault
    summary_label = histogram_metric.label.add()
    summary_label.name, summary_label.value = "kind", "fs"
    summary_label = histogram_metric.label.add()
    summary_label.name, summary_label.value = "app", "vault"

    for upper_bound, cumulative_count in [
        (0.001, 2),
        (0.002, 2),
        (0.004, 2),
        (0.008, 2),
        (0.016, 4),
        (0.032, 4),
        (0.064, 4),
        (0.128, 4),
        (0.256, 4),
        (0.512, 4),
        (1.024, 4),
        (2.048, 4),
        (4.096, 4),
        (8.192, 4),
        (float('inf'), 4),
    ]:
        bucket = histogram_metric.histogram.bucket.add()
        bucket.upper_bound = upper_bound
        bucket.cumulative_count = cumulative_count

    # Root histogram sample
    histogram_metric.histogram.sample_count = 4
    histogram_metric.histogram.sample_sum = 0.026131671

    # Kubernetes
    histogram_metric = expected_etcd_metric.metric.add()

    # Label for app kubernetes
    summary_label = histogram_metric.label.add()
    summary_label.name, summary_label.value = "kind", "fs"
    summary_label = histogram_metric.label.add()
    summary_label.name, summary_label.value = "app", "kubernetes"

    for upper_bound, cumulative_count in [
        (0.001, 718),
        (0.002, 740),
        (0.004, 743),
        (0.008, 748),
        (0.016, 751),
        (0.032, 751),
        (0.064, 751),
        (0.128, 751),
        (0.256, 751),
        (0.512, 751),
        (1.024, 751),
        (2.048, 751),
        (4.096, 751),
        (8.192, 751),
        (float('inf'), 751),
    ]:
        bucket = histogram_metric.histogram.bucket.add()
        bucket.upper_bound = upper_bound
        bucket.cumulative_count = cumulative_count

    # Root histogram sample
    histogram_metric.histogram.sample_count = 751
    histogram_metric.histogram.sample_sum = 0.3097010759999998

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    check = p_check
    metrics = [k for k in check.parse_metric_family(response)]

    assert 1 == len(metrics)

    current_metric = metrics[0]
    # in metrics with more than one label
    # the labels don't always get parsed in a deterministic order
    # deconstruct the metric to ensure it's equal
    assert expected_etcd_metric.help == current_metric.help
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    for idx in range(len(expected_etcd_metric.metric)):
        assert expected_etcd_metric.metric[idx].summary == current_metric.metric[idx].summary
        for label in expected_etcd_metric.metric[idx].label:
            assert label in current_metric.metric[idx].label


def test_parse_one_summary(p_check):
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

    expected_etcd_metric = metrics_pb2.MetricFamily()
    expected_etcd_metric.help = "The HTTP response sizes in bytes."
    expected_etcd_metric.name = "http_response_size_bytes"
    expected_etcd_metric.type = 2

    summary_metric = expected_etcd_metric.metric.add()

    # Label for prometheus handler
    summary_label = summary_metric.label.add()
    summary_label.name, summary_label.value = "handler", "prometheus"

    # Root summary sample
    summary_metric.summary.sample_count = 5
    summary_metric.summary.sample_sum = 120512

    # Create quantiles 0.5, 0.9, 0.99
    quantile_05 = summary_metric.summary.quantile.add()
    quantile_05.quantile = 0.5
    quantile_05.value = 24547

    quantile_09 = summary_metric.summary.quantile.add()
    quantile_09.quantile = 0.9
    quantile_09.value = 25763

    quantile_099 = summary_metric.summary.quantile.add()
    quantile_099.quantile = 0.99
    quantile_099.value = 25763

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    check = p_check
    metrics = [k for k in check.parse_metric_family(response)]

    assert 1 == len(metrics)
    current_metric = metrics[0]
    assert expected_etcd_metric == current_metric


def test_parse_two_summaries_with_labels(p_check):
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

    expected_etcd_metric = metrics_pb2.MetricFamily()
    expected_etcd_metric.help = "The HTTP response sizes in bytes."
    expected_etcd_metric.name = "http_response_size_bytes"
    expected_etcd_metric.type = 2

    # Metric from internet #
    summary_metric_from_internet = expected_etcd_metric.metric.add()

    # Label for prometheus handler
    summary_label = summary_metric_from_internet.label.add()
    summary_label.name, summary_label.value = "handler", "prometheus"

    summary_label = summary_metric_from_internet.label.add()
    summary_label.name, summary_label.value = "from", "internet"

    # Root summary sample
    summary_metric_from_internet.summary.sample_count = 5
    summary_metric_from_internet.summary.sample_sum = 120512

    # Create quantiles 0.5, 0.9, 0.99
    quantile_05 = summary_metric_from_internet.summary.quantile.add()
    quantile_05.quantile = 0.5
    quantile_05.value = 24547

    quantile_09 = summary_metric_from_internet.summary.quantile.add()
    quantile_09.quantile = 0.9
    quantile_09.value = 25763

    quantile_099 = summary_metric_from_internet.summary.quantile.add()
    quantile_099.quantile = 0.99
    quantile_099.value = 25763

    # Metric from cluster #
    summary_metric_from_cluster = expected_etcd_metric.metric.add()

    # Label for prometheus handler
    summary_label = summary_metric_from_cluster.label.add()
    summary_label.name, summary_label.value = "handler", "prometheus"

    summary_label = summary_metric_from_cluster.label.add()
    summary_label.name, summary_label.value = "from", "cluster"

    # Root summary sample
    summary_metric_from_cluster.summary.sample_count = 4
    summary_metric_from_cluster.summary.sample_sum = 94913

    # Create quantiles 0.5, 0.9, 0.99
    quantile_05 = summary_metric_from_cluster.summary.quantile.add()
    quantile_05.quantile = 0.5
    quantile_05.value = 24615

    quantile_09 = summary_metric_from_cluster.summary.quantile.add()
    quantile_09.quantile = 0.9
    quantile_09.value = 24627

    quantile_099 = summary_metric_from_cluster.summary.quantile.add()
    quantile_099.quantile = 0.99
    quantile_099.value = 24627

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    check = p_check
    metrics = [k for k in check.parse_metric_family(response)]

    assert 1 == len(metrics)

    current_metric = metrics[0]
    # in metrics with more than one label
    # the labels don't always get parsed in a deterministic order
    # deconstruct the metric to ensure it's equal
    assert expected_etcd_metric.help == current_metric.help
    assert expected_etcd_metric.name == current_metric.name
    assert expected_etcd_metric.type == current_metric.type
    for idx in range(len(expected_etcd_metric.metric)):
        assert expected_etcd_metric.metric[idx].summary == current_metric.metric[idx].summary
        for label in expected_etcd_metric.metric[idx].label:
            assert label in current_metric.metric[idx].label


def test_parse_one_summary_with_none_values(p_check):
    text_data = (
        '# HELP http_response_size_bytes The HTTP response sizes in bytes.\n'
        '# TYPE http_response_size_bytes summary\n'
        'http_response_size_bytes{handler="prometheus",quantile="0.5"} NaN\n'
        'http_response_size_bytes{handler="prometheus",quantile="0.9"} NaN\n'
        'http_response_size_bytes{handler="prometheus",quantile="0.99"} NaN\n'
        'http_response_size_bytes_sum{handler="prometheus"} 0\n'
        'http_response_size_bytes_count{handler="prometheus"} 0\n'
    )

    expected_etcd_metric = metrics_pb2.MetricFamily()
    expected_etcd_metric.help = "The HTTP response sizes in bytes."
    expected_etcd_metric.name = "http_response_size_bytes"
    expected_etcd_metric.type = 2

    summary_metric = expected_etcd_metric.metric.add()

    # Label for prometheus handler
    summary_label = summary_metric.label.add()
    summary_label.name, summary_label.value = "handler", "prometheus"

    # Root summary sample
    summary_metric.summary.sample_count = 0
    summary_metric.summary.sample_sum = 0.0

    # Create quantiles 0.5, 0.9, 0.99
    quantile_05 = summary_metric.summary.quantile.add()
    quantile_05.quantile = 0.5
    quantile_05.value = float('nan')

    quantile_09 = summary_metric.summary.quantile.add()
    quantile_09.quantile = 0.9
    quantile_09.value = float('nan')

    quantile_099 = summary_metric.summary.quantile.add()
    quantile_099.quantile = 0.99
    quantile_099.value = float('nan')

    # Iter on the generator to get all metrics
    response = MockResponse(text_data, 'text/plain; version=0.0.4')
    check = p_check
    metrics = [k for k in check.parse_metric_family(response)]
    assert 1 == len(metrics)
    current_metric = metrics[0]
    # As the NaN value isn't supported when we are calling assertEqual
    # we need to compare the object representation instead of the object itself
    assert expected_etcd_metric.__repr__() == current_metric.__repr__()


def test_label_joins(sorted_tags_check):
    """Tests label join on text format"""
    text_data = None
    f_name = os.path.join(FIXTURES_PATH, 'ksm.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check = sorted_tags_check
        check.NAMESPACE = 'ksm'
        check.label_joins = {
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

        check.metrics_mapper = {
            'kube_pod_status_ready': 'pod.ready',
            'kube_pod_status_scheduled': 'pod.scheduled',
            'kube_deployment_status_replicas': 'deploy.replicas.available',
        }

        check.gauge = mock.MagicMock()
        # dry run to build mapping
        check.process("http://fake.endpoint:10055/metrics")
        # run with submit
        check.process("http://fake.endpoint:10055/metrics")

        # check a bunch of metrics
        check.gauge.assert_has_calls(
            [
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:event-exporter-v0.1.7-958884745-qgnbw',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.32.3.14',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-6dj58',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.132.0.7',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-z348z',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                            'pod_ip:11.132.0.14',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:heapster-v1.4.3-2027615481-lmjm5',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                            'pod_ip:11.32.5.7',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:kube-dns-3092422022-lvrmx',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.32.3.10',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:kube-dns-3092422022-x0tjx',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.32.3.9',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:kube-dns-autoscaler-97162954-mf6d3',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                            'pod_ip:11.32.5.6',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:kube-proxy-gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.132.0.7',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.scheduled',
                    1.0,
                    sorted(
                        [
                            'pod:ungaged-panther-kube-state-metrics-3918010230-64xwc',
                            'namespace:default',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                            'pod_ip:11.32.5.45',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.scheduled',
                    1.0,
                    sorted(
                        [
                            'pod:event-exporter-v0.1.7-958884745-qgnbw',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.32.3.14',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.scheduled',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-6dj58',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.132.0.7',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.scheduled',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-z348z',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                            'pod_ip:11.132.0.14',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.scheduled',
                    1.0,
                    sorted(
                        [
                            'pod:heapster-v1.4.3-2027615481-lmjm5',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                            'pod_ip:11.32.5.7',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.scheduled',
                    1.0,
                    sorted(
                        [
                            'pod:kube-dns-3092422022-lvrmx',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.32.3.10',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.scheduled',
                    1.0,
                    sorted(
                        [
                            'pod:kube-dns-3092422022-x0tjx',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.32.3.9',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.deploy.replicas.available',
                    1.0,
                    sorted(
                        [
                            'namespace:kube-system',
                            'deployment:event-exporter-v0.1.7',
                            'label_k8s_app:event-exporter',
                            'label_addonmanager_kubernetes_io_mode:Reconcile',
                            'label_kubernetes_io_cluster_service:true',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.deploy.replicas.available',
                    1.0,
                    sorted(
                        [
                            'namespace:kube-system',
                            'deployment:heapster-v1.4.3',
                            'label_k8s_app:heapster',
                            'label_addonmanager_kubernetes_io_mode:Reconcile',
                            'label_kubernetes_io_cluster_service:true',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.deploy.replicas.available',
                    2.0,
                    sorted(
                        [
                            'namespace:kube-system',
                            'deployment:kube-dns',
                            'label_kubernetes_io_cluster_service:true',
                            'label_addonmanager_kubernetes_io_mode:Reconcile',
                            'label_k8s_app:kube-dns',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.deploy.replicas.available',
                    1.0,
                    sorted(
                        [
                            'namespace:kube-system',
                            'deployment:kube-dns-autoscaler',
                            'label_kubernetes_io_cluster_service:true',
                            'label_addonmanager_kubernetes_io_mode:Reconcile',
                            'label_k8s_app:kube-dns-autoscaler',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.deploy.replicas.available',
                    1.0,
                    sorted(
                        [
                            'namespace:kube-system',
                            'deployment:kubernetes-dashboard',
                            'label_kubernetes_io_cluster_service:true',
                            'label_addonmanager_kubernetes_io_mode:Reconcile',
                            'label_k8s_app:kubernetes-dashboard',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.deploy.replicas.available',
                    1.0,
                    sorted(
                        [
                            'namespace:kube-system',
                            'deployment:l7-default-backend',
                            'label_k8s_app:glbc',
                            'label_addonmanager_kubernetes_io_mode:Reconcile',
                            'label_kubernetes_io_cluster_service:true',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.deploy.replicas.available',
                    1.0,
                    sorted(['namespace:kube-system', 'deployment:tiller-deploy']),
                    hostname=None,
                ),
                mock.call(
                    'ksm.deploy.replicas.available',
                    1.0,
                    sorted(['namespace:default', 'deployment:ungaged-panther-kube-state-metrics']),
                    hostname=None,
                ),
            ],
            any_order=True,
        )


def test_label_joins_gc(sorted_tags_check):
    """Tests label join GC on text format"""
    text_data = None
    f_name = os.path.join(FIXTURES_PATH, 'ksm.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check = sorted_tags_check
        check.NAMESPACE = 'ksm'
        check.label_joins = {'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node', 'pod_ip']}}
        check.metrics_mapper = {'kube_pod_status_ready': 'pod.ready'}
        check.gauge = mock.MagicMock()
        # dry run to build mapping
        check.process("http://fake.endpoint:10055/metrics")
        # run with submit
        check.process("http://fake.endpoint:10055/metrics")
        # check a bunch of metrics
        check.gauge.assert_has_calls(
            [
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-6dj58',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                            'pod_ip:11.132.0.7',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-z348z',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                            'pod_ip:11.132.0.14',
                        ]
                    ),
                    hostname=None,
                ),
            ],
            any_order=True,
        )
        assert 15 == len(check._label_mapping['pod'])
        text_data = text_data.replace('dd-agent-62bgh', 'dd-agent-1337')

    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check.process("http://fake.endpoint:10055/metrics")
        assert 'dd-agent-1337' in check._label_mapping['pod']
        assert 'dd-agent-62bgh' not in check._label_mapping['pod']
        assert 15 == len(check._label_mapping['pod'])


def test_label_joins_missconfigured(sorted_tags_check):
    """Tests label join missconfigured label is ignored"""
    text_data = None
    f_name = os.path.join(FIXTURES_PATH, 'ksm.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check = sorted_tags_check
        check.NAMESPACE = 'ksm'
        check.label_joins = {'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node', 'not_existing']}}
        check.metrics_mapper = {'kube_pod_status_ready': 'pod.ready'}
        check.gauge = mock.MagicMock()
        # dry run to build mapping
        check.process("http://fake.endpoint:10055/metrics")
        # run with submit
        check.process("http://fake.endpoint:10055/metrics")
        # check a bunch of metrics
        check.gauge.assert_has_calls(
            [
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-6dj58',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                        ]
                    ),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-z348z',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                        ]
                    ),
                    hostname=None,
                ),
            ],
            any_order=True,
        )


def test_label_join_not_existing(sorted_tags_check):
    """Tests label join on non existing matching label is ignored"""
    text_data = None
    f_name = os.path.join(FIXTURES_PATH, 'ksm.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check = sorted_tags_check
        check.NAMESPACE = 'ksm'
        check.label_joins = {'kube_pod_info': {'label_to_match': 'not_existing', 'labels_to_get': ['node', 'pod_ip']}}
        check.metrics_mapper = {'kube_pod_status_ready': 'pod.ready'}
        check.gauge = mock.MagicMock()
        # dry run to build mapping
        check.process("http://fake.endpoint:10055/metrics")
        # run with submit
        check.process("http://fake.endpoint:10055/metrics")
        # check a bunch of metrics
        check.gauge.assert_has_calls(
            [
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(['pod:fluentd-gcp-v2.0.9-6dj58', 'namespace:kube-system', 'condition:true']),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(['pod:fluentd-gcp-v2.0.9-z348z', 'namespace:kube-system', 'condition:true']),
                    hostname=None,
                ),
            ],
            any_order=True,
        )


def test_label_join_metric_not_existing(sorted_tags_check):
    """Tests label join on non existing metric is ignored"""
    text_data = None
    f_name = os.path.join(FIXTURES_PATH, 'ksm.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check = sorted_tags_check
        check.NAMESPACE = 'ksm'
        check.label_joins = {'not_existing': {'label_to_match': 'pod', 'labels_to_get': ['node', 'pod_ip']}}
        check.metrics_mapper = {'kube_pod_status_ready': 'pod.ready'}
        check.gauge = mock.MagicMock()
        # dry run to build mapping
        check.process("http://fake.endpoint:10055/metrics")
        # run with submit
        check.process("http://fake.endpoint:10055/metrics")
        # check a bunch of metrics
        check.gauge.assert_has_calls(
            [
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(['pod:fluentd-gcp-v2.0.9-6dj58', 'namespace:kube-system', 'condition:true']),
                    hostname=None,
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(['pod:fluentd-gcp-v2.0.9-z348z', 'namespace:kube-system', 'condition:true']),
                    hostname=None,
                ),
            ],
            any_order=True,
        )


def test_label_join_with_hostname(sorted_tags_check):
    """Tests label join and hostname override on a metric"""
    text_data = None
    f_name = os.path.join(FIXTURES_PATH, 'ksm.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_response = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
    )
    with mock.patch('requests.get', return_value=mock_response, __name__="get"):
        check = sorted_tags_check
        check.NAMESPACE = 'ksm'
        check.label_joins = {'kube_pod_info': {'label_to_match': 'pod', 'labels_to_get': ['node']}}
        check.label_to_hostname = 'node'
        check.metrics_mapper = {'kube_pod_status_ready': 'pod.ready'}
        check.gauge = mock.MagicMock()
        # dry run to build mapping
        check.process("http://fake.endpoint:10055/metrics")
        # run with submit
        check.process("http://fake.endpoint:10055/metrics")
        # check a bunch of metrics
        check.gauge.assert_has_calls(
            [
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-6dj58',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                        ]
                    ),
                    hostname='gke-foobar-test-kube-default-pool-9b4ff111-0kch',
                ),
                mock.call(
                    'ksm.pod.ready',
                    1.0,
                    sorted(
                        [
                            'pod:fluentd-gcp-v2.0.9-z348z',
                            'namespace:kube-system',
                            'condition:true',
                            'node:gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                        ]
                    ),
                    hostname='gke-foobar-test-kube-default-pool-9b4ff111-j75z',
                ),
            ],
            any_order=True,
        )


@pytest.fixture()
def mock_get():
    text_data = None
    f_name = os.path.join(FIXTURES_PATH, 'ksm.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_get = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    )

    try:
        yield mock_get.start()
    finally:
        mock_get.stop()


def test_health_service_check_ok(mock_get):
    """Tests endpoint health service check OK"""
    check = PrometheusCheck('prometheus_check', {}, {}, {})
    check.NAMESPACE = 'ksm'
    check.health_service_check = True
    check.service_check = mock.MagicMock()
    check.process("http://fake.endpoint:10055/metrics")
    check.service_check.assert_called_with(
        "ksm.prometheus.health", PrometheusCheck.OK, tags=["endpoint:http://fake.endpoint:10055/metrics"]
    )


def test_health_service_check_failing():
    """Tests endpoint health service check failing"""
    check = PrometheusCheck('prometheus_check', {}, {}, {})
    check.NAMESPACE = 'ksm'
    check.health_service_check = True
    check.service_check = mock.MagicMock()
    with pytest.raises(requests.ConnectionError):
        check.process("http://fake.endpoint:10055/metrics")
    check.service_check.assert_called_with(
        "ksm.prometheus.health", PrometheusCheck.CRITICAL, tags=["endpoint:http://fake.endpoint:10055/metrics"]
    )


def test_set_prometheus_timeout():
    """Tests set_prometheus_timeout function call from a PrometheusCheck"""
    # no timeout specified, should be default 10
    check = PrometheusCheck('prometheus_check', {}, {}, {})
    instance_default = {
        'prometheus_url': 'http://localhost:10249/metrics',
        'namespace': 'foobar',
        'metrics': ['metric3'],
    }
    check.set_prometheus_timeout(instance_default)
    assert check.prometheus_timeout == 10

    # timeout set to 3
    check2 = PrometheusCheck('prometheus_check', {}, {}, {})
    instance_timeout_set = {
        'prometheus_timeout': 3,
        'prometheus_url': 'http://localhost:10249/metrics',
        'namespace': 'foobar',
        'metrics': ['metric3'],
    }
    check2.set_prometheus_timeout(instance_timeout_set)
    assert check2.prometheus_timeout == 3


def test_text_filter_input():
    check = PrometheusCheck('prometheus_check', {}, {}, {})
    check._text_filter_blacklist = ["string1", "string2"]

    lines_in = [
        "line with string3",
        "line with string1",
        "line with string2",
        "line with string1 and string2",
        "line with string",
    ]
    expected_out = ["line with string3", "line with string"]

    filtered = [x for x in check._text_filter_input(lines_in)]
    assert filtered == expected_out


def test_ssl_verify_not_raise_warning(caplog, mocked_prometheus_check, text_data):
    check = mocked_prometheus_check

    with caplog.at_level(logging.DEBUG):
        resp = check.poll('https://httpbin.org/get')

    assert 'httpbin.org' in resp.content.decode('utf-8')

    expected_message = 'An unverified HTTPS request is being made to https://httpbin.org/get'
    for _, _, message in caplog.record_tuples:
        assert message != expected_message


def test_ssl_verify_not_raise_warning_cert_false(caplog, mocked_prometheus_check, text_data):
    check = mocked_prometheus_check
    check.ssl_ca_cert = False

    with caplog.at_level(logging.DEBUG):
        resp = check.poll('https://httpbin.org/get')

    assert 'httpbin.org' in resp.content.decode('utf-8')

    expected_message = 'An unverified HTTPS request is being made to https://httpbin.org/get'
    for _, _, message in caplog.record_tuples:
        assert message != expected_message


def test_requests_wrapper_config():
    instance_http = {
        'prometheus_endpoint': 'http://localhost:8080',
        'extra_headers': {'foo': 'bar'},
        'auth_type': 'digest',
        'username': 'data',
        'password': 'dog',
        'tls_cert': '/path/to/cert',
    }
    init_config_http = {'timeout': 42}
    check = PrometheusCheck('prometheus_check', init_config_http, {}, [instance_http])

    expected_headers = OrderedDict(
        [
            ('User-Agent', 'Datadog Agent/0.0.0'),
            ('Accept', '*/*'),
            ('Accept-Encoding', 'gzip'),
            ('foo', 'bar'),
            ('accept-encoding', 'gzip'),
            (
                'accept',
                'application/vnd.google.protobuf; proto=io.prometheus.client.MetricFamily; encoding=delimited',
            ),
        ]
    )

    with mock.patch("requests.get") as get:
        check.poll(instance_http['prometheus_endpoint'], instance=instance_http)
        get.assert_called_with(
            instance_http['prometheus_endpoint'],
            stream=False,
            headers=expected_headers,
            auth=requests.auth.HTTPDigestAuth('data', 'dog'),
            cert='/path/to/cert',
            timeout=(42.0, 42.0),
            proxies=None,
            verify=True,
            allow_redirects=True,
        )

        check.poll(instance_http['prometheus_endpoint'])
        get.assert_called_with(
            instance_http['prometheus_endpoint'],
            stream=False,
            headers=expected_headers,
            auth=requests.auth.HTTPDigestAuth('data', 'dog'),
            cert='/path/to/cert',
            timeout=(42.0, 42.0),
            proxies=None,
            verify=True,
            allow_redirects=True,
        )
