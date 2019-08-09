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

    def test__build_similar_elements__service_check_message(self, aggregator):
        check = AgentCheck()

        check.service_check('test.similar1', AgentCheck.OK, message="aa")
        check.service_check('test.similar2', AgentCheck.OK, message="bb")
        check.service_check('test.similar3', AgentCheck.OK, message="cc")
        check.service_check('test.similar4', AgentCheck.OK, message="dd")

        expected_service_check = ServiceCheckStub(
            None, "test.similar", status=AgentCheck.OK, tags=None, hostname=None, message="cc"
        )
        similar_service_checks = similar._build_similar_elements(expected_service_check, aggregator._service_checks)

        # expect similar metrics in a similarity order
        assert similar_service_checks[0][1].name == 'test.similar3'

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
