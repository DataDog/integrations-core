# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import time

import pytest
from datadog_test_libs.utils.mock_dns import mock_local
from kafka import KafkaConsumer

from datadog_checks.dev import WaitFor, docker_run

from .common import DOCKER_IMAGE_PATH, HOST_IP, KAFKA_CONNECT_STR, TOPICS
from .runners import KConsumer, Producer


def find_topics():
    consumer = KafkaConsumer(bootstrap_servers=KAFKA_CONNECT_STR, request_timeout_ms=1000)
    topics = consumer.topics()

    # We expect to find 2 topics: `marvel` and `dc`
    return len(topics) == 2


def initialize_topics():
    consumer = KConsumer(TOPICS)

    with Producer():
        with consumer:
            time.sleep(5)


@pytest.fixture(scope='session')
def mock_local_kafka_hosts_dns():
    mapping = {'kafka1': ('127.0.0.1', 9092), 'kafka2': ('127.0.0.1', 9093)}
    with mock_local(mapping):
        yield


@pytest.fixture(scope='session')
def dd_environment(mock_local_kafka_hosts_dns, e2e_instance):
    """
    Start a kafka cluster and wait for it to be up and running.
    """
    with docker_run(
        DOCKER_IMAGE_PATH,
        conditions=[WaitFor(find_topics, attempts=60, wait=3), WaitFor(initialize_topics)],
        env_vars={
            # Advertising the hostname doesn't work on docker:dind so we manually
            # resolve the IP address. This seems to also work outside docker:dind
            # so we got that goin for us.
            'KAFKA_HOST': HOST_IP
        },
    ):
        yield e2e_instance, E2E_METADATA


E2E_METADATA = {
    'custom_hosts': [('kafka1', '127.0.0.1'), ('kafka2', '127.0.0.1')],
    'start_commands': [
        'apt-get update',
        'apt-get install -y build-essential',
    ],
}


# @pytest.fixture(scope='session')
# def zk_instance():
#     return {
#         'kafka_connect_str': KAFKA_CONNECT_STR,
#         'zk_connect_str': ZK_CONNECT_STR,
#         'consumer_groups': {'my_consumer': {'marvel': [0]}},
#     }


@pytest.fixture(scope='session')
def kafka_instance():
    return {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'kafka_consumer_offsets': True,
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
        'broker_requests_batch_size': 1,
    }


# Dummy TLS certs
CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')
cert = os.path.join(CERTIFICATE_DIR, 'cert.cert')
private_key = os.path.join(CERTIFICATE_DIR, 'server.pem')


@pytest.fixture(scope='session')
def kafka_instance_tls():
    return {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'kafka_consumer_offsets': True,
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
        'broker_requests_batch_size': 1,
        'use_tls': True,
        'tls_validate_hostname': True,
        'tls_cert': cert,
        'tls_private_key': private_key,
        'tls_ca_cert': CERTIFICATE_DIR,
    }


@pytest.fixture(scope='session')
def e2e_instance(kafka_instance):
    return kafka_instance
