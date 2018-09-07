# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.envoy import Envoy
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS
from .common import INSTANCES, response


class TestEnvoy:
    CHECK_NAME = 'envoy'

    def test_success(self, aggregator):
        instance = INSTANCES['main']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])
        c.check(instance)

        metrics_collected = 0
        for metric in METRICS.keys():
            metrics_collected += len(aggregator.metrics(METRIC_PREFIX + metric))

        assert metrics_collected >= 250

    def test_success_fixture(self, aggregator):
        instance = INSTANCES['main']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('multiple_services')):
            c.check(instance)

        metrics_collected = 0
        for metric in METRICS.keys():
            metrics_collected += len(aggregator.metrics(METRIC_PREFIX + metric))

        num_metrics = len(response('multiple_services').content.decode().splitlines())
        num_metrics -= sum(c.unknown_metrics.values()) + sum(c.unknown_tags.values())
        assert 4150 <= metrics_collected == num_metrics

    def test_success_fixture_whitelist(self, aggregator):
        instance = INSTANCES['whitelist']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('multiple_services')):
            c.check(instance)

        for metric in aggregator.metric_names:
            assert metric.startswith('envoy.cluster.')

    def test_success_fixture_blacklist(self, aggregator):
        instance = INSTANCES['blacklist']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('multiple_services')):
            c.check(instance)

        for metric in aggregator.metric_names:
            assert not metric.startswith('envoy.cluster.')

    def test_success_fixture_whitelist_blacklist(self, aggregator):
        instance = INSTANCES['whitelist_blacklist']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('multiple_services')):
            c.check(instance)

        for metric in aggregator.metric_names:
            assert metric.startswith("envoy.cluster.") and not metric.startswith("envoy.cluster.out")

    def test_service_check(self, aggregator):
        instance = INSTANCES['main']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('multiple_services')):
            c.check(instance)

        assert aggregator.service_checks(Envoy.SERVICE_CHECK_NAME)[0].status == Envoy.OK

    def test_unknown(self):
        instance = INSTANCES['main']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('unknown_metrics')):
            c.check(instance)

        assert sum(c.unknown_metrics.values()) == 5
