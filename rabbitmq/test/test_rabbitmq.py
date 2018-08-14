# # (C) Datadog, Inc. 2010-2017
# # All rights reserved
# # Licensed under Simplified BSD License (see LICENSE)
#
# # stdlib
# import sys
# import os
#
# # 3p
# import mock
# import requests
# from nose.plugins.attrib import attr
# import pika
#
# # project
# from checks import AgentCheck
# from tests.checks.common import AgentCheckTest
#
# @attr(requires='rabbitmq')
# class TestRabbitMQ(AgentCheckTest):
#
#     CHECK_NAME = 'rabbitmq'
#
#     @classmethod
#     def setUpClass(cls):
#         sys.path.append(os.path.abspath('.'))
#
#     @classmethod
#     def tearDownClass(cls):
#         sys.path.pop()
#
#     def test__get_data(self):
#         with mock.patch('datadog_checks.rabbitmq.rabbitmq.requests') as r:
#             from datadog_checks.rabbitmq import RabbitMQ  # pylint: disable=import-error,no-name-in-module
#             from datadog_checks.rabbitmq.rabbitmq import RabbitMQException  # pylint: disable=import-error,no-name-in-module
#             check = RabbitMQ('rabbitmq', {}, {"instances": [{"rabbitmq_api_url": "http://example.com"}]})
#             r.get.side_effect = [requests.exceptions.HTTPError, ValueError]
#             self.assertRaises(RabbitMQException, check._get_data, '')
#             self.assertRaises(RabbitMQException, check._get_data, '')
#
#     def test_status_check(self):
#         self.run_check({"instances": [{"rabbitmq_api_url": "http://example.com"}]})
#         self.assertEqual(len(self.service_checks), 1)
#         sc = self.service_checks[0]
#         self.assertEqual(sc['check'], 'rabbitmq.status')
#         self.assertEqual(sc['status'], AgentCheck.CRITICAL)
#
#         # test aliveness service_checks on server down
#         self.check.cached_vhosts = {"http://example.com/": ["vhost1", "vhost2"]}
#         self.run_check({"instances": [{"rabbitmq_api_url": "http://example.com"}]})
#         self.assertEqual(len(self.service_checks), 3)
#         sc = self.service_checks[0]
#         self.assertEqual(sc['check'], 'rabbitmq.status')
#         self.assertEqual(sc['status'], AgentCheck.CRITICAL)
#
#         sc = self.service_checks[1]
#         self.assertEqual(sc['check'], 'rabbitmq.aliveness')
#         self.assertEqual(sc['status'], AgentCheck.CRITICAL)
#         self.assertEqual(sc['tags'], [u'vhost:vhost1'])
#
#         sc = self.service_checks[2]
#         self.assertEqual(sc['check'], 'rabbitmq.aliveness')
#         self.assertEqual(sc['status'], AgentCheck.CRITICAL)
#         self.assertEqual(sc['tags'], [u'vhost:vhost2'])
#
#
#         self.check._get_data = mock.MagicMock()
#         self.run_check({"instances": [{"rabbitmq_api_url": "http://example.com"}]})
#         self.assertEqual(len(self.service_checks), 1)
#         sc = self.service_checks[0]
#         self.assertEqual(sc['check'], 'rabbitmq.status')
#         self.assertEqual(sc['status'], AgentCheck.OK)
#
#     def test__check_aliveness(self):
#         instances = {"instances": [{"rabbitmq_api_url": "http://example.com"}]}
#         self.load_check(instances)
#         self.check._get_data = mock.MagicMock()
#
#         # only one vhost should be OK
#         self.check._get_data.side_effect = [{"status": "ok"}, {}]
#         self.check._check_aliveness(instances['instances'][0], '', vhosts=['foo', 'bar'], custom_tags=[])
#         sc = self.check.get_service_checks()
#
#         self.assertEqual(len(sc), 2)
#         self.assertEqual(sc[0]['check'], 'rabbitmq.aliveness')
#         self.assertEqual(sc[0]['status'], AgentCheck.OK)
#         self.assertEqual(sc[1]['check'], 'rabbitmq.aliveness')
#         self.assertEqual(sc[1]['status'], AgentCheck.CRITICAL)
#
#         # in case of connection errors, this check should stay silent
#         from datadog_checks.rabbitmq.rabbitmq import RabbitMQException  # pylint: disable=import-error,no-name-in-module
#         self.check._get_data.side_effect = RabbitMQException
#         self.assertRaises(RabbitMQException, self.check._get_vhosts, instances['instances'][0], '')
