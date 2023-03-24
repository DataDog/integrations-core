# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os
import time

import pytest
from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev._env import e2e_testing
from datadog_checks.kafka_consumer import KafkaCheck

from .common import AUTHENTICATION, DOCKER_IMAGE_PATH, HERE, KAFKA_CONNECT_STR, LEGACY_CLIENT, TOPICS
from .runners import KConsumer, Producer

CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'docker', 'ssl', 'certificate')
ROOT_CERTIFICATE = os.path.join(CERTIFICATE_DIR, 'caroot.pem')
CERTIFICATE = os.path.join(CERTIFICATE_DIR, 'cert.pem')
PRIVATE_KEY = os.path.join(CERTIFICATE_DIR, 'key.pem')
PRIVATE_KEY_PASSWORD = 'secret'

if LEGACY_CLIENT:
    E2E_METADATA = {
        'custom_hosts': [('kafka1', '127.0.0.1'), ('kafka2', '127.0.0.1')],
        'start_commands': [
            'apt-get update',
            'apt-get install -y build-essential',
            'bash /tmp/start_commands.sh',
        ],
        'docker_volumes': [
            f'{HERE}/scripts/start_commands.sh:/tmp/start_commands.sh',
            f'{HERE}/docker/ssl/certificate:/tmp/certificate',
        ],
    }
else:
    E2E_METADATA = {
        'custom_hosts': [('kafka1', '127.0.0.1'), ('kafka2', '127.0.0.1')],
        'docker_volumes': [
            f'{HERE}/scripts/start_commands.sh:/tmp/start_commands.sh',
            f'{HERE}/docker/ssl/certificate:/tmp/certificate',
        ],
        'start_commands': ['bash /tmp/start_commands.sh'],
    }

if AUTHENTICATION == "ssl":
    INSTANCE = {
        'kafka_connect_str': "localhost:9092",
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
        'broker_requests_batch_size': 1,
        'security_protocol': 'SSL',
        'tls_cert': CERTIFICATE,
        'tls_private_key': PRIVATE_KEY,
        'tls_private_key_password': PRIVATE_KEY_PASSWORD,
        'tls_ca_cert': ROOT_CERTIFICATE,
        'use_legacy_client': LEGACY_CLIENT,
    }
else:
    INSTANCE = {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
        'broker_requests_batch_size': 1,
        'use_legacy_client': LEGACY_CLIENT,
    }

E2E_INSTANCE = copy.deepcopy(INSTANCE)

if AUTHENTICATION == "ssl":
    E2E_INSTANCE["tls_cert"] = "/tmp/certificate/cert.pem"
    E2E_INSTANCE["tls_private_key"] = "/tmp/certificate/key.pem"
    E2E_INSTANCE["tls_ca_cert"] = "/tmp/certificate/caroot.pem"


@pytest.fixture(scope='session')
def dd_environment():
    """
    Start a kafka cluster and wait for it to be up and running.
    """
    with docker_run(
        DOCKER_IMAGE_PATH,
        conditions=[
            WaitFor(create_topics, attempts=60, wait=3),
            WaitFor(initialize_topics),
        ],
    ):
        yield {
            'instances': [E2E_INSTANCE],
            'init_config': {'kafka_timeout': 30},
        }, E2E_METADATA


@pytest.fixture
def check():
    return lambda instance, init_config=None: KafkaCheck('kafka_consumer', init_config or {}, [instance])


@pytest.fixture
def kafka_instance():
    return copy.deepcopy(E2E_INSTANCE) if e2e_testing() else copy.deepcopy(INSTANCE)


def create_topics():
    client = _create_admin_client()

    for topic in TOPICS:
        client.create_topics([NewTopic(topic, 2, 1)], operation_timeout=1, request_timeout=1)

    return set(client.list_topics(timeout=1).topics.keys()) == set(TOPICS)


def initialize_topics():
    with Producer(INSTANCE):
        with KConsumer(INSTANCE, TOPICS):
            time.sleep(5)


def _create_admin_client():
    config = {
        "bootstrap.servers": INSTANCE['kafka_connect_str'],
        "socket.timeout.ms": 1000,
    }

    if INSTANCE.get('security_protocol', 'PLAINTEXT') == "SSL":
        config.update(
            {
                "security.protocol": "ssl",
                "ssl.ca.location": INSTANCE.get("tls_ca_cert"),
                "ssl.certificate.location": INSTANCE.get("tls_cert"),
                "ssl.key.location": INSTANCE.get("tls_private_key"),
                "ssl.key.password": INSTANCE.get("tls_private_key_password"),
            }
        )

    return AdminClient(config)
