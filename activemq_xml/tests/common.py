# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname

CHECK_NAME = 'activemq_xml'

HERE = os.path.dirname(os.path.abspath(__file__))

URL = "http://{}:8161".format(get_docker_hostname())

CONFIG = {
    'url': URL,
    'username': "admin",
    'password': "admin"
}

GENERAL_METRICS = [
    "activemq.subscriber.count",
    "activemq.topic.count",
    "activemq.queue.count",
]

QUEUE_METRICS = [
    "activemq.queue.consumer_count",
    "activemq.queue.dequeue_count",
    "activemq.queue.enqueue_count",
    "activemq.queue.size",
]

SUBSCRIBER_METRICS = [
    "activemq.subscriber.pending_queue_size",
    "activemq.subscriber.dequeue_counter",
    "activemq.subscriber.enqueue_counter",
    "activemq.subscriber.dispatched_queue_size",
    "activemq.subscriber.dispatched_counter",
]

TOPIC_METRICS = [
    "activemq.topic.consumer_count",
    "activemq.topic.dequeue_count",
    "activemq.topic.enqueue_count",
    "activemq.topic.size",
]
