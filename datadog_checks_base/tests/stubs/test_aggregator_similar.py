# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import difflib

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs import similar
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.common import HistogramBucketStub, MetricStub, ServiceCheckStub


class TestSimilarAssertionMessages(object):
    def test_build_similar_elements_msg(self, aggregator):
        check = AgentCheck()

        check.gauge('test.another_similar_metric', 0)
        check.gauge('test.very_different_metric', 0)
        check.gauge('test.most_similar_metric', 0)
        check.gauge('test.very_very_different', 0)

        expected_metric = MetricStub("test.similar_metric", None, None, None, None, None)
        actual_msg = similar.build_similar_elements_msg(expected_metric, aggregator._metrics).strip()

        expected_msg = '''
    Expected:
        MetricStub(name='test.similar_metric', type=None, value=None, tags=None, hostname=None, device=None, flush_first_value=None)
Similar submitted:
Score   Most similar
0.88    MetricStub(name='test.most_similar_metric', type=0, value=0.0, tags=[], hostname='', device=None, flush_first_value=False)
0.83    MetricStub(name='test.another_similar_metric', type=0, value=0.0, tags=[], hostname='', device=None, flush_first_value=False)
0.62    MetricStub(name='test.very_different_metric', type=0, value=0.0, tags=[], hostname='', device=None, flush_first_value=False)
0.42    MetricStub(name='test.very_very_different', type=0, value=0.0, tags=[], hostname='', device=None, flush_first_value=False)
    '''.strip()  # noqa: E501
        delta = difflib.ndiff([expected_msg], [actual_msg])
        assert expected_msg == actual_msg, delta

    def test__build_similar_elements__metric_name(self, aggregator):
        check = AgentCheck()

        check.gauge('test.another_similar_metric', 0)
        check.gauge('test.very_different_metric', 0)
        check.gauge('test.most_similar_metric', 0)
        check.gauge('test.very_very_different', 0)

        expected_metric = MetricStub(
            "test.similar_metric", type=None, value=None, tags=None, hostname=None, device=None
        )
        similar_metrics = similar._build_similar_elements(expected_metric, aggregator._metrics)

        expected_most_similar_metric = similar_metrics[0][1]
        expected_second_most_similar_metric = similar_metrics[1][1]

        assert expected_most_similar_metric.name == 'test.most_similar_metric'
        assert expected_second_most_similar_metric.name == 'test.another_similar_metric'

    def test__build_similar_elements__metric_value(self, aggregator):
        check = AgentCheck()

        check.gauge('test.similar_metric1', 10)
        check.gauge('test.similar_metric2', 20)
        check.gauge('test.similar_metric3', 30)

        expected_metric = MetricStub("test.my_metric", type=None, value=20, tags=None, hostname=None, device=None)
        similar_metrics = similar._build_similar_elements(expected_metric, aggregator._metrics)

        expected_most_similar_metric = similar_metrics[0][1]
        print(similar_metrics)

        assert expected_most_similar_metric.name == 'test.similar_metric2'

    def test__build_similar_elements__metric_tags(self, aggregator):
        check = AgentCheck()

        check.gauge('test.similar_metric2', 10, tags=['name:less_similar_tag'])
        check.gauge('test.similar_metric1', 10, tags=['name:similar_tag'])
        check.gauge('test.similar_metric3', 10, tags=['something:different'])

        expected_metric = MetricStub(
            "test.test.similar_metric", type=None, value=10, tags=['name:similar_tag'], hostname=None, device=None
        )
        similar_metrics = similar._build_similar_elements(expected_metric, aggregator._metrics)

        # expect similar metrics in a similarity order
        assert similar_metrics[0][1].name == 'test.similar_metric1'
        assert similar_metrics[1][1].name == 'test.similar_metric2'
        assert similar_metrics[2][1].name == 'test.similar_metric3'

    def test__build_similar_elements__metric_hostname(self, aggregator):
        check = AgentCheck()

        check.gauge('test.similar_metric2', 10, hostname='less_similar_host')
        check.gauge('test.similar_metric1', 10, hostname='similar_host')
        check.gauge('test.similar_metric3', 10, hostname='different')

        expected_metric = MetricStub(
            "test.test.similar_metric", type=None, value=10, tags=None, hostname='similar_host', device=None
        )
        similar_metrics = similar._build_similar_elements(expected_metric, aggregator._metrics)

        # expect similar metrics in a similarity order
        assert similar_metrics[0][1].name == 'test.similar_metric1'
        assert similar_metrics[1][1].name == 'test.similar_metric2'
        assert similar_metrics[2][1].name == 'test.similar_metric3'

    def test__build_similar_elements__metric_device(self, aggregator):
        metrics = {
            'test.similar_metric2': [
                MetricStub('test.similar_metric2', AggregatorStub.GAUGE, 10, [], None, 'less_similar_device')
            ],
            'test.similar_metric1': [
                MetricStub('test.similar_metric1', AggregatorStub.GAUGE, 10, [], None, 'similar_device')
            ],
            'test.similar_metric3': [
                MetricStub('test.similar_metric3', AggregatorStub.GAUGE, 10, [], None, 'different')
            ],
        }

        expected_metric = MetricStub(
            "test.test.similar_metric", type=None, value=10, tags=None, hostname=None, device='similar_device'
        )
        similar_metrics = similar._build_similar_elements(expected_metric, metrics)

        # expect similar metrics in a similarity order
        assert similar_metrics[0][1].name == 'test.similar_metric1'
        assert similar_metrics[1][1].name == 'test.similar_metric2'
        assert similar_metrics[2][1].name == 'test.similar_metric3'

    def test__build_similar_elements__service_check_name(self, aggregator):
        check = AgentCheck()

        check.service_check('test.second_similar_service_check', AgentCheck.OK)
        check.service_check('test.very_different_service_check', AgentCheck.OK)
        check.service_check('test.most_similar_service_check', AgentCheck.OK)
        check.service_check('test.very_very_different', AgentCheck.OK)

        expected_service_check = ServiceCheckStub(
            None, "test.similar_service_check", status=AgentCheck.OK, tags=None, hostname=None, message=None
        )
        similar_service_checks = similar._build_similar_elements(expected_service_check, aggregator._service_checks)

        # expect similar metrics in a similarity order
        assert similar_service_checks[0][1].name == 'test.most_similar_service_check'
        assert similar_service_checks[1][1].name == 'test.second_similar_service_check'
        assert similar_service_checks[2][1].name == 'test.very_different_service_check'
        assert similar_service_checks[3][1].name == 'test.very_very_different'

    def test__build_similar_elements__service_check_status(self, aggregator):
        check = AgentCheck()

        check.service_check('test.similar1', AgentCheck.OK)
        check.service_check('test.similar2', AgentCheck.CRITICAL)
        check.service_check('test.similar3', AgentCheck.WARNING)

        expected_service_check = ServiceCheckStub(
            None, "test.similar", status=AgentCheck.CRITICAL, tags=None, hostname=None, message=None
        )
        similar_service_checks = similar._build_similar_elements(expected_service_check, aggregator._service_checks)

        # expect similar metrics in a similarity order
        assert similar_service_checks[0][1].name == 'test.similar2'

    def test__build_similar_elements__service_check_tags(self, aggregator):
        check = AgentCheck()

        check.service_check('test.similar2', AgentCheck.OK, tags=['name:less_similar_tag'])
        check.service_check('test.similar1', AgentCheck.OK, tags=['name:similar_tag'])
        check.service_check('test.similar3', AgentCheck.OK, tags=['something:different'])

        expected_service_check = ServiceCheckStub(
            None, "test.similar", status=AgentCheck.OK, tags=['name:similar_tag'], hostname=None, message=None
        )
        similar_service_checks = similar._build_similar_elements(expected_service_check, aggregator._service_checks)

        # expect similar metrics in a similarity order
        assert similar_service_checks[0][1].name == 'test.similar1'
        assert similar_service_checks[1][1].name == 'test.similar2'
        assert similar_service_checks[2][1].name == 'test.similar3'

    def test__build_similar_elements__service_check_hostname(self, aggregator):
        check = AgentCheck()

        check.service_check('test.similar1', AgentCheck.OK, hostname="aa")
        check.service_check('test.similar2', AgentCheck.OK, hostname="bb")
        check.service_check('test.similar3', AgentCheck.OK, hostname="cc")
        check.service_check('test.similar4', AgentCheck.OK, hostname="dd")

        expected_service_check = ServiceCheckStub(
            None, "test.similar", status=AgentCheck.OK, tags=None, hostname="cc", message=None
        )
        similar_service_checks = similar._build_similar_elements(expected_service_check, aggregator._service_checks)

        # expect similar metrics in a similarity order
        assert similar_service_checks[0][1].name == 'test.similar3'

    def test__build_similar_elements__histogram_buckets(self, aggregator):
        check = AgentCheck()

        check.submit_histogram_bucket('histogram.bucket3', 1, 0.0, 10.0, True, "hostname", ["tag2"])
        check.submit_histogram_bucket('histogram.bucket2', 1, 125.0, 312.0, True, "hostname", ["tag1"])
        check.submit_histogram_bucket('histogram.bucket1', 1, 0.0, 10.0, True, "hostname", ["tag1"])
        check.submit_histogram_bucket('histogram.bucket4', 1, 125.0, 312.0, True, "hostname2", ["tag1"])
        check.submit_histogram_bucket('histogram.bucket5', 1, 125.0, 312.0, True, "hostname2", ["tag2"])
        check.submit_histogram_bucket('histogram.bucket0', 2, 125.0, 312.0, False, "hostname2", ["tag2"])

        expected_histogram_bucket = HistogramBucketStub('histogram.bucket', 1, 0.0, 10.0, True, "hostname", ["tag1"])
        similar_histogram_bucket = similar._build_similar_elements(
            expected_histogram_bucket, aggregator._histogram_buckets
        )

        # expect buckets in closest similarity order
        assert similar_histogram_bucket[0][1].name == 'histogram.bucket1'  # exact match (except name)
        assert similar_histogram_bucket[1][1].name == 'histogram.bucket3'  # value/upper/lower/monotonic/host match
        assert similar_histogram_bucket[2][1].name == 'histogram.bucket2'  # value/monotonic/host/tag match
        assert similar_histogram_bucket[3][1].name == 'histogram.bucket4'  # value/monotonic/tag match
        assert similar_histogram_bucket[4][1].name == 'histogram.bucket5'  # value/monotonic match
        assert similar_histogram_bucket[5][1].name == 'histogram.bucket0'  # no match
