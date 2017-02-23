# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import sys

# 3p
import mock
import requests
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest, get_checksd_path, get_os

CONFIG = {
    'init_config': {},
    'instances': [
        {
            'rabbitmq_api_url': 'http://localhost:15672/api/',
            'rabbitmq_user': 'guest',
            'rabbitmq_pass': 'guest',
            'queues': ['test1'],
        }
    ]
}

CONFIG_REGEX = {
    'init_config': {},
    'instances': [
        {
            'rabbitmq_api_url': 'http://localhost:15672/api/',
            'rabbitmq_user': 'guest',
            'rabbitmq_pass': 'guest',
            'queues_regexes': ['test\d+'],
        }
    ]
}

CONFIG_WITH_FAMILY = {
    'init_config': {},
    'instances': [
        {
            'rabbitmq_api_url': 'http://localhost:15672/api/',
            'rabbitmq_user': 'guest',
            'rabbitmq_pass': 'guest',
            'tag_families': True,
            'queues_regexes': ['(test)\d+'],
        }
    ]
}

COMMON_METRICS = [
    'rabbitmq.node.fd_used',
    'rabbitmq.node.mem_used',
    'rabbitmq.node.run_queue',
    'rabbitmq.node.sockets_used',
    'rabbitmq.node.partitions'
]

Q_METRICS = [
    'consumers',
    'memory',
    'messages',
    'messages.rate',
    'messages_ready',
    'messages_ready.rate',
    'messages_unacknowledged',
    'messages_unacknowledged.rate',
    'messages.publish.count',
    'messages.publish.rate',
]

@attr(requires='rabbitmq')
class RabbitMQCheckTest(AgentCheckTest):
    CHECK_NAME = 'rabbitmq'

    def test_check(self):
        self.run_check(CONFIG)

        # Node attributes
        for mname in COMMON_METRICS:
            self.assertMetricTagPrefix(mname, 'rabbitmq_node', count=1)

        self.assertMetric('rabbitmq.node.partitions', value=0, count=1)

        # Queue attributes, should be only one queue fetched
        # TODO: create a 'fake consumer' and get missing metrics
        # active_consumers, acks, delivers, redelivers
        for mname in Q_METRICS:
            self.assertMetricTag('rabbitmq.queue.%s' %
                                 mname, 'rabbitmq_queue:test1', count=1)

        self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:/'])
        self.assertServiceCheckOK('rabbitmq.status')

        self.coverage_report()

    def test_queue_regex(self):
        self.run_check(CONFIG_REGEX)

        # Node attributes
        for mname in COMMON_METRICS:
            self.assertMetricTagPrefix(mname, 'rabbitmq_node', count=1)

        for mname in Q_METRICS:
            self.assertMetricTag('rabbitmq.queue.%s' %
                                 mname, 'rabbitmq_queue:test1', count=1)
            self.assertMetricTag('rabbitmq.queue.%s' %
                                 mname, 'rabbitmq_queue:test5', count=1)
            self.assertMetricTag('rabbitmq.queue.%s' %
                                 mname, 'rabbitmq_queue:tralala', count=0)

        self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:/'])
        self.assertServiceCheckOK('rabbitmq.status')

        self.coverage_report()

    def test_family_tagging(self):
        self.run_check(CONFIG_WITH_FAMILY)

        # Node attributes
        for mname in COMMON_METRICS:
            self.assertMetricTagPrefix(mname, 'rabbitmq_node', count=1)

        for mname in Q_METRICS:
            self.assertMetricTag('rabbitmq.queue.%s' %
                                 mname, 'rabbitmq_queue_family:test', count=2)

        self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:/'])
        self.assertServiceCheckOK('rabbitmq.status')

        self.coverage_report()

@attr(requires='rabbitmq')
class TestRabbitMQ(AgentCheckTest):

    CHECK_NAME = 'rabbitmq'

    @classmethod
    def setUpClass(cls):
        sys.path.append(get_checksd_path(get_os()))

    @classmethod
    def tearDownClass(cls):
        sys.path.pop()

    def test__get_data(self):
        with mock.patch('check.requests') as r:
            from check import RabbitMQ, RabbitMQException  # pylint: disable=import-error
            check = RabbitMQ('rabbitmq', {}, {"instances": [{"rabbitmq_api_url": "http://example.com"}]})
            r.get.side_effect = [requests.exceptions.HTTPError, ValueError]
            self.assertRaises(RabbitMQException, check._get_data, '')
            self.assertRaises(RabbitMQException, check._get_data, '')

    def test_status_check(self):
        self.run_check({"instances": [{"rabbitmq_api_url": "http://example.com"}]})
        self.assertEqual(len(self.service_checks), 1)
        sc = self.service_checks[0]
        self.assertEqual(sc['check'], 'rabbitmq.status')
        self.assertEqual(sc['status'], AgentCheck.CRITICAL)

        self.check._get_data = mock.MagicMock()
        self.run_check({"instances": [{"rabbitmq_api_url": "http://example.com"}]})
        self.assertEqual(len(self.service_checks), 1)
        sc = self.service_checks[0]
        self.assertEqual(sc['check'], 'rabbitmq.status')
        self.assertEqual(sc['status'], AgentCheck.OK)

    def test__check_aliveness(self):
        self.load_check({"instances": [{"rabbitmq_api_url": "http://example.com"}]})
        self.check._get_data = mock.MagicMock()

        # only one vhost should be OK
        self.check._get_data.side_effect = [{"status": "ok"}, {}]
        self.check._check_aliveness('', vhosts=['foo', 'bar'])
        sc = self.check.get_service_checks()

        self.assertEqual(len(sc), 2)
        self.assertEqual(sc[0]['check'], 'rabbitmq.aliveness')
        self.assertEqual(sc[0]['status'], AgentCheck.OK)
        self.assertEqual(sc[1]['check'], 'rabbitmq.aliveness')
        self.assertEqual(sc[1]['status'], AgentCheck.CRITICAL)

        # in case of connection errors, this check should stay silent
        from check import RabbitMQException  # pylint: disable=import-error
        self.check._get_data.side_effect = RabbitMQException
        self.assertRaises(RabbitMQException, self.check._check_aliveness, '')
