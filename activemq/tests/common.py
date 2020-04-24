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

JVM_E2E_METRICS = [
    'jvm.buffer_pool.direct.capacity',
    'jvm.buffer_pool.direct.count',
    'jvm.buffer_pool.direct.used',
    'jvm.buffer_pool.mapped.capacity',
    'jvm.buffer_pool.mapped.count',
    'jvm.buffer_pool.mapped.used',
    'jvm.cpu_load.process',
    'jvm.cpu_load.system',
    'jvm.gc.cms.count',
    'jvm.gc.eden_size',
    'jvm.gc.old_gen_size',
    'jvm.gc.parnew.time',
    'jvm.gc.survivor_size',
    'jvm.heap_memory',
    'jvm.heap_memory_committed',
    'jvm.heap_memory_init',
    'jvm.heap_memory_max',
    'jvm.loaded_classes',
    'jvm.non_heap_memory',
    'jvm.non_heap_memory_committed',
    'jvm.non_heap_memory_init',
    'jvm.non_heap_memory_max',
    'jvm.os.open_file_descriptors',
    'jvm.thread_count',
]
