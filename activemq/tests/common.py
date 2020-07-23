# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here

CHECK_NAME = 'activemq'

HERE = get_here()
HOST = get_docker_hostname()

JMX_PORT = 1616

TEST_QUEUES = ('FOO_QUEUE', 'TEST_QUEUE')
TEST_TOPICS = ('FOO_TOPIC', 'TEST_TOPIC')
TEST_MESSAGE = {'body': 'test_message'}
TEST_AUTH = ('admin', 'admin')

TEST_PORT = 8161
BASE_URL = 'http://{}:{}/api/message'.format(HOST, TEST_PORT)

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
