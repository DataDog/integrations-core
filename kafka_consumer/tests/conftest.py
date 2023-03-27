# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os
import time

import pytest
from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic

from datadog_checks.dev import TempDir, WaitFor, docker_run
from datadog_checks.dev._env import e2e_testing
from datadog_checks.kafka_consumer import KafkaCheck

from .common import AUTHENTICATION, DOCKER_IMAGE_PATH, HERE, KAFKA_CONNECT_STR, TOPICS, get_authentication_configuration
from .runners import Consumer, Producer

CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'docker', 'ssl', 'certificate')
ROOT_CERTIFICATE = os.path.join(CERTIFICATE_DIR, 'caroot.pem')
CERTIFICATE = os.path.join(CERTIFICATE_DIR, 'cert.pem')
PRIVATE_KEY = os.path.join(CERTIFICATE_DIR, 'key.pem')
PRIVATE_KEY_PASSWORD = 'secret'

E2E_METADATA = {
    'custom_hosts': [('kafka1', '127.0.0.1'), ('kafka2', '127.0.0.1')],
    'docker_volumes': [
        f'{HERE}/docker/ssl/certificate:/tmp/certificate',
        f'{HERE}/docker/kerberos/kdc/krb5_agent.conf:/etc/krb5.conf',
    ],
}

if AUTHENTICATION == "ssl":
    INSTANCE = {
        'kafka_connect_str': "localhost:9092",
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
        'security_protocol': 'SSL',
        'tls_cert': CERTIFICATE,
        'tls_private_key': PRIVATE_KEY,
        'tls_private_key_password': PRIVATE_KEY_PASSWORD,
        'tls_ca_cert': ROOT_CERTIFICATE,
    }
elif AUTHENTICATION == "kerberos":
    INSTANCE = {
        'kafka_connect_str': "localhost:9092",
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
        "sasl_mechanism": "GSSAPI",
        "sasl_kerberos_service_name": "kafka",
        "security_protocol": "SASL_PLAINTEXT",
        # Real path will be replaced once the temp dir will be created in `dd_environment`
        "sasl_kerberos_keytab": "{}/localhost.key",
        "sasl_kerberos_principal": "kafka/localhost",
    }
else:
    INSTANCE = {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
    }

E2E_INSTANCE = copy.deepcopy(INSTANCE)

if AUTHENTICATION == "ssl":
    E2E_INSTANCE["tls_cert"] = "/tmp/certificate/cert.pem"
    E2E_INSTANCE["tls_private_key"] = "/tmp/certificate/key.pem"
    E2E_INSTANCE["tls_ca_cert"] = "/tmp/certificate/caroot.pem"
elif AUTHENTICATION == "kerberos":
    E2E_INSTANCE["sasl_kerberos_keytab"] = "/var/lib/secret/localhost.key"


@pytest.fixture(scope='session')
def dd_environment():
    with TempDir() as secret_dir:
        os.chmod(secret_dir, 0o777)
        """
        Start a kafka cluster and wait for it to be up and running.
        """

        conditions = []

        if AUTHENTICATION == "kerberos":
            INSTANCE["sasl_kerberos_keytab"] = INSTANCE["sasl_kerberos_keytab"].format(secret_dir)
            conditions.append(WaitFor(wait_for_cp_kafka_topics, attempts=10, wait=10))
            E2E_METADATA["docker_volumes"].append(f"{secret_dir}:/var/lib/secret")

        conditions.extend(
            [
                WaitFor(create_topics, attempts=60, wait=3),
                WaitFor(initialize_topics),
            ]
        )

        with docker_run(
            DOCKER_IMAGE_PATH,
            conditions=conditions,
            env_vars={
                "KRB5_CONFIG": f"{HERE}/docker/kerberos/kdc/krb5_agent.conf",
                "SECRET_DIR": secret_dir,
            },
            build=True,
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

    if set(TOPICS).issubset(set(client.list_topics(timeout=1).topics.keys())):
        return True

    for topic in TOPICS:
        client.create_topics([NewTopic(topic, 2, 1)])
        time.sleep(1)

    # Make sure the topics in `TOPICS` are created. Brokers may have more topics (such as internal topics)
    # so we only check if it contains the topic we need.
    return set(TOPICS).issubset(set(client.list_topics(timeout=1).topics.keys()))


def wait_for_cp_kafka_topics():
    client = _create_admin_client()
    topics = {
        '_confluent_balancer_partition_samples',
        '_confluent_balancer_api_state',
        '_confluent_balancer_broker_samples',
        '_confluent-telemetry-metrics',
        '_confluent-command',
    }
    return topics.issubset(set(client.list_topics(timeout=1).topics.keys()))


def initialize_topics():
    with Producer(INSTANCE):
        with Consumer(INSTANCE, TOPICS):
            time.sleep(5)


def _create_admin_client():
    config = {
        "bootstrap.servers": INSTANCE['kafka_connect_str'],
        "socket.timeout.ms": 1000,
        "topic.metadata.refresh.interval.ms": 2000,
    }
    config.update(get_authentication_configuration(INSTANCE))

    return AdminClient(config)
