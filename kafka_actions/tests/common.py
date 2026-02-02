# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import socket

from confluent_kafka.admin import AdminClient

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
HOST_IP = socket.gethostbyname(HOST)
KAFKA_CONNECT_STR = f'{HOST_IP}:9092'
TEST_TOPIC = 'test-topic'

DOCKER_IMAGE_PATH = os.path.join(HERE, 'docker', "docker-compose.yaml")

E2E_METADATA = {}


def get_cluster_id():
    config = {
        "bootstrap.servers": KAFKA_CONNECT_STR,
        "socket.timeout.ms": 1000,
        "topic.metadata.refresh.interval.ms": 2000,
    }
    client = AdminClient(config)
    try:
        return client.list_topics(timeout=5).cluster_id
    except Exception:
        return None


INSTANCE = {
    'remote_config_id': 'test-rc-id',
    'kafka_connect_str': KAFKA_CONNECT_STR,
    'action': 'read_messages',
    'read_messages': {
        'cluster': '',  # Will be filled in by test
        'topic': TEST_TOPIC,
        'partition': -1,
        'start_offset': -2,  # earliest
        'n_messages_retrieved': 5,
        'max_scanned_messages': 100,
        'value_format': 'json',
        'key_format': 'string',
    },
}

E2E_INSTANCE = copy.deepcopy(INSTANCE)
