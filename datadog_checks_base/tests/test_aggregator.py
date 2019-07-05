# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import MetricStub


class TestSimilarMetrics(object):
    def test_message_output(self, aggregator):
        check = AgentCheck()

        check.gauge('test.most_similar_metric', 0)
        check.gauge('test.another_similar_metric', 0)
        check.gauge('test.very_different_metric', 0)
        check.gauge('test.very_very_different', 0)

        expected_metric = MetricStub("test.similar_metric", None, None, None, None)
        actual_msg = aggregator._similar_metrics_msg(expected_metric)

        expected_msg = '''
Expected metric:
        MetricStub(name='test.similar_metric', type=None, value=None, tags=None, hostname=None)
Similar submitted metrics:
Score   Metric
0.44    MetricStub(name='test.most_similar_metric', type=0, value=0.0, tags=[], hostname='')
0.41    MetricStub(name='test.another_similar_metric', type=0, value=0.0, tags=[], hostname='')
0.31    MetricStub(name='test.very_different_metric', type=0, value=0.0, tags=[], hostname='')
0.21    MetricStub(name='test.very_very_different', type=0, value=0.0, tags=[], hostname='')
        '''
        assert expected_msg.strip() == actual_msg.strip()

    def test__get_similar_metrics__metric_name(self, aggregator):
        check = AgentCheck()

        check.gauge('test.most_similar_metric', 0)
        check.gauge('test.another_similar_metric', 0)
        check.gauge('test.very_different_metric', 0)
        check.gauge('test.very_very_different', 0)

        expected_metric = MetricStub("test.similar_metric", type=None, value=None, tags=None, hostname=None)
        similar_metrics = aggregator._get_similar_metrics(expected_metric)

        expected_most_similar_metric = similar_metrics[0][1]
        expected_second_most_similar_metric = similar_metrics[1][1]

        assert expected_most_similar_metric.name == 'test.most_similar_metric'
        assert expected_second_most_similar_metric.name == 'test.another_similar_metric'

    def test__get_similar_metrics__metric_value(self, aggregator):
        check = AgentCheck()

        check.gauge('test.similar_metric1', 10)
        check.gauge('test.similar_metric2', 20)
        check.gauge('test.similar_metric3', 30)

        expected_metric = MetricStub("test.my_metric", type=None, value=20, tags=None, hostname=None)
        similar_metrics = aggregator._get_similar_metrics(expected_metric)

        expected_most_similar_metric = similar_metrics[0][1]
        print(similar_metrics)

        assert expected_most_similar_metric.name == 'test.similar_metric2'

    def test__get_similar_metrics__metric_tags(self, aggregator):
        check = AgentCheck()

        check.gauge('test.similar_metric1', 10, tags=['name:similar_tag'])
        check.gauge('test.similar_metric2', 10, tags=['name:less_similar_tag'])
        check.gauge('test.similar_metric3', 10, tags=['something:different'])

        expected_metric = MetricStub("test.test.similar_metric", type=None, value=10, tags=['name:similar_tag'], hostname=None)
        similar_metrics = aggregator._get_similar_metrics(expected_metric)

        # expect similar metrics in a similarity order
        assert similar_metrics[0][1].name == 'test.similar_metric1'
        assert similar_metrics[1][1].name == 'test.similar_metric2'
        assert similar_metrics[2][1].name == 'test.similar_metric3'

    def test__get_similar_metrics__metric_hostname(self, aggregator):
        check = AgentCheck()

        check.gauge('test.similar_metric2', 10, hostname='less_similar_host')
        check.gauge('test.similar_metric1', 10, hostname='similar_host')
        check.gauge('test.similar_metric3', 10, hostname='different')

        expected_metric = MetricStub("test.test.similar_metric", type=None, value=10, tags=None, hostname='similar_host')
        similar_metrics = aggregator._get_similar_metrics(expected_metric)

        # expect similar metrics in a similarity order
        assert similar_metrics[0][1].name == 'test.similar_metric1'
        assert similar_metrics[1][1].name == 'test.similar_metric2'
        assert similar_metrics[2][1].name == 'test.similar_metric3'
