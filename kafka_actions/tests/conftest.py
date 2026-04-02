# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import time

import pytest
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev._env import e2e_testing
from datadog_checks.kafka_actions import KafkaActionsCheck

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    """
    Start a kafka cluster and wait for it to be up and running.
    """
    conditions = [
        WaitFor(create_topic, attempts=60, wait=3),
        WaitFor(initialize_topic),
        WaitFor(is_cluster_id_available),
    ]

    with docker_run(
        common.DOCKER_IMAGE_PATH,
        conditions=conditions,
        build=True,
    ):
        yield (
            {
                'instances': [common.E2E_INSTANCE],
            },
            common.E2E_METADATA,
        )


def is_cluster_id_available():
    return common.get_cluster_id() is not None


@pytest.fixture
def check():
    return lambda instance: KafkaActionsCheck('kafka_actions', {}, [instance])


@pytest.fixture
def kafka_instance():
    instance = copy.deepcopy(common.E2E_INSTANCE if e2e_testing() else common.INSTANCE)
    # Set the cluster ID
    cluster_id = common.get_cluster_id()
    if cluster_id:
        instance['read_messages']['cluster'] = cluster_id
    return instance


def create_topic():
    client = _create_admin_client()
    response = client.list_topics(timeout=1)

    if common.TEST_TOPIC in response.topics.keys():
        return True

    client.create_topics([NewTopic(common.TEST_TOPIC, 2, 1)])
    time.sleep(1)

    return common.TEST_TOPIC in client.list_topics(timeout=1).topics.keys()


def initialize_topic():
    """Produce some test messages to the topic."""
    producer_config = {
        "bootstrap.servers": common.KAFKA_CONNECT_STR,
    }
    producer = Producer(producer_config)

    # Produce 10 test messages
    for i in range(10):
        message = {
            'id': i,
            'status': 'active' if i % 2 == 0 else 'inactive',
            'value': i * 10,
        }
        producer.produce(common.TEST_TOPIC, key=f'key-{i}'.encode('utf-8'), value=json.dumps(message).encode('utf-8'))

    producer.flush()
    time.sleep(2)
    return True


def _create_admin_client():
    config = {
        "bootstrap.servers": common.KAFKA_CONNECT_STR,
        "socket.timeout.ms": 5000,
        "topic.metadata.refresh.interval.ms": 2000,
    }
    return AdminClient(config)
