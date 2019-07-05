# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs import similar
from datadog_checks.base.stubs.common import MetricStub, ServiceCheckStub


class TestSimilarAssertionMessages(object):
    def test_build_similar_elements_msg(self, aggregator):
        check = AgentCheck()

        check.gauge('test.another_similar_metric', 0)
        check.gauge('test.very_different_metric', 0)
        check.gauge('test.most_similar_metric', 0)
        check.gauge('test.very_very_different', 0)

        expected_metric = MetricStub("test.similar_metric", None, None, None, None)
        actual_msg = similar.build_similar_elements_msg(expected_metric, aggregator._metrics)

        expected_msg = '''
Expected:
        MetricStub(name='test.similar_metric', type=None, value=None, tags=None, hostname=None)
Similar submitted:
Score   Most similar
0.88    MetricStub(name='test.most_similar_metric', type=0, value=0.0, tags=[], hostname='')
0.83    MetricStub(name='test.another_similar_metric', type=0, value=0.0, tags=[], hostname='')
0.62    MetricStub(name='test.very_different_metric', type=0, value=0.0, tags=[], hostname='')
0.42    MetricStub(name='test.very_very_different', type=0, value=0.0, tags=[], hostname='')
        '''
        assert expected_msg.strip() == actual_msg.strip(), "Actual message:\n" + actual_msg

    def test__build_similar_elements__metric_name(self, aggregator):
        check = AgentCheck()

        check.gauge('test.another_similar_metric', 0)
        check.gauge('test.very_different_metric', 0)
        check.gauge('test.most_similar_metric', 0)
        check.gauge('test.very_very_different', 0)

        expected_metric = MetricStub("test.similar_metric", type=None, value=None, tags=None, hostname=None)
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

        expected_metric = MetricStub("test.my_metric", type=None, value=20, tags=None, hostname=None)
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
            "test.test.similar_metric", type=None, value=10, tags=['name:similar_tag'], hostname=None
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
            "test.test.similar_metric", type=None, value=10, tags=None, hostname='similar_host'
        )
        similar_metrics = similar._build_similar_elements(expected_metric, aggregator._metrics)

        # expect similar metrics in a similarity order
        assert similar_metrics[0][1].name == 'test.similar_metric1'
        assert similar_metrics[1][1].name == 'test.similar_metric2'
        assert similar_metrics[2][1].name == 'test.similar_metric3'

    def test__get_similar_service_check__metric_name(self, aggregator):
        check = AgentCheck()

        check.service_check('test.second_similar_service_check', AgentCheck.OK)
        check.service_check('test.very_different_service_check', AgentCheck.OK)
        check.service_check('test.most_similar_service_check', AgentCheck.OK)
        check.service_check('test.very_very_different', AgentCheck.OK)

        expected_metric = ServiceCheckStub(
            None, "test.similar_service_check", status=AgentCheck.OK, tags=None, hostname=None, message=None
        )
        similar_metrics = similar._build_similar_elements(expected_metric, aggregator._service_checks)

        # expect similar metrics in a similarity order
        assert similar_metrics[0][1].name == 'test.most_similar_service_check'
        assert similar_metrics[1][1].name == 'test.second_similar_service_check'
        assert similar_metrics[2][1].name == 'test.very_different_service_check'
        assert similar_metrics[3][1].name == 'test.very_very_different'
