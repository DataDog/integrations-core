# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.jmx import JVM_E2E_METRICS

CHECK_NAME = 'activemq'

COMPOSE_FILE = os.getenv('COMPOSE_FILE')
IS_ARTEMIS = COMPOSE_FILE == 'artemis.yaml'

artemis = pytest.mark.skipif(not IS_ARTEMIS, reason='Test only valid for ActiveMQ Artemis versions')
not_artemis = pytest.mark.skipif(IS_ARTEMIS, reason='Test only valid for non-Artemis versions')

HERE = get_here()
HOST = get_docker_hostname()

JMX_PORT = 1616

TEST_QUEUES = ('FOO_QUEUE', 'TEST_QUEUE')
TEST_TOPICS = ('FOO_TOPIC', 'TEST_TOPIC')
TEST_MESSAGE = {'body': 'test_message'}
TEST_AUTH = ('admin', 'admin')

TEST_PORT = 8161
BASE_URL = 'http://{}:{}'.format(HOST, TEST_PORT)
ACTIVEMQ_URL = '{}/api/message'.format(BASE_URL)
ARTEMIS_URL = '{}/console/jolokia'.format(BASE_URL)

# not all metrics will be available in our E2E environment, specifically:
# "activemq.queue.dequeue_count",
# "activemq.queue.dispatch_count",
# "activemq.queue.enqueue_count",
# "activemq.queue.expired_count",
# "activemq.queue.in_flight_count",

ACTIVEMQ_E2E_METRICS = [
    "activemq.queue.avg_enqueue_time",
    "activemq.queue.consumer_count",
    "activemq.queue.producer_count",
    "activemq.queue.max_enqueue_time",
    "activemq.queue.min_enqueue_time",
    "activemq.queue.memory_pct",
    "activemq.queue.size",
    "activemq.broker.store_pct",
    "activemq.broker.temp_pct",
    "activemq.broker.memory_pct",
]

ARTEMIS_E2E_METRICS = [
    "activemq.artemis.address.bytes_per_page",
    "activemq.artemis.address.number_of_messages",
    "activemq.artemis.address.pages_count",
    "activemq.artemis.address.routed_messages",
    "activemq.artemis.address.size",
    "activemq.artemis.address.unrouted_messages",
    "activemq.artemis.address_memory_usage",
    "activemq.artemis.address_memory_usage_pct",
    "activemq.artemis.connection_count",
    "activemq.artemis.disk_store_usage_pct",
    "activemq.artemis.max_disk_usage",
    "activemq.artemis.queue.consumer_count",
    "activemq.artemis.queue.max_consumers",
    "activemq.artemis.queue.message_count",
    "activemq.artemis.queue.messages_acknowledged",
    "activemq.artemis.queue.messages_added",
    "activemq.artemis.queue.messages_expired",
    "activemq.artemis.queue.messages_killed",
    "activemq.artemis.total_connection_count",
    "activemq.artemis.total_consumer_count",
    "activemq.artemis.total_message_count",
    "activemq.artemis.total_messages_acknowledged",
    "activemq.artemis.total_messages_added",
]

OPTIONAL_ARTEMIS_E2E_METRICS = {
    "activemq.artemis.address.number_of_messages",
}

ACTIVEMQ_E2E_JVM_METRICS = list(JVM_E2E_METRICS)
ACTIVEMQ_E2E_JVM_METRICS.remove('jvm.gc.cms.count')
ACTIVEMQ_E2E_JVM_METRICS.remove('jvm.gc.parnew.time')
