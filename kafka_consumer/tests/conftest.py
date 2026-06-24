# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os
import time

import mock
import pytest
from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic

from datadog_checks.dev import TempDir, WaitFor, docker_run
from datadog_checks.dev._env import e2e_testing
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.client import KafkaClient
from datadog_checks.kafka_consumer.connectors import KafkaConnectCollector

from . import common
from .common import get_cluster_id
from .runners import Consumer, Producer


def seed_mock_kafka_client():
    """Minimal Kafka client mock sufficient for the connector-focused tests."""
    client = mock.create_autospec(KafkaClient)
    client.consumer_get_cluster_id_and_list_topics.return_value = ('cluster-1', [])
    client.list_consumer_groups.return_value = []
    client.list_consumer_group_offsets.return_value = []
    client._cluster_metadata = None
    return client


SAMPLE_CONNECTORS_RESPONSE = {
    'demo-source': {
        'info': {
            'type': 'source',
            'config': {
                'connector.class': 'org.apache.kafka.connect.mirror.MirrorSourceConnector',
                'tasks.max': '2',
                'topics': 'demo-orders',
            },
        },
        'status': {
            'connector': {'state': 'RUNNING'},
            'tasks': [
                {'id': 0, 'state': 'RUNNING', 'worker_id': 'connect:8083'},
                {'id': 1, 'state': 'RUNNING', 'worker_id': 'connect:8083'},
            ],
        },
    },
    'demo-heartbeat': {
        'info': {
            'type': 'source',
            'config': {'connector.class': 'org.apache.kafka.connect.mirror.MirrorHeartbeatConnector'},
        },
        'status': {
            'connector': {'state': 'PAUSED'},
            'tasks': [{'id': 0, 'state': 'PAUSED', 'worker_id': 'connect:8083'}],
        },
    },
}


@pytest.fixture
def make_collector():
    def _make(connect_urls=None, cache_store=None):
        check = mock.MagicMock()
        check.OK = 0
        check.WARNING = 1
        check.CRITICAL = 2

        if cache_store is None:
            cache_store = {}

        def read_cache(key):
            return cache_store.get(key, '')

        def write_cache(key, value):
            cache_store[key] = value

        check.read_persistent_cache.side_effect = read_cache
        check.write_persistent_cache.side_effect = write_cache

        config = mock.MagicMock()
        config._kafka_connect_urls = connect_urls or []
        config._kafka_connect_username = None
        config._kafka_connect_password = None
        config._kafka_connect_tls_verify = True
        config._kafka_connect_tls_ca_cert = None
        config._kafka_connect_tls_cert = None
        config._kafka_connect_tls_key = None
        config._kafka_connect_oauth_token_provider = None
        config._kafka_configs_refresh_interval = 3600
        config._request_timeout = 10
        config._custom_tags = []
        config._kafka_cluster_id_override = None
        config._auto_detected_cluster_id = ''
        config._get_tags.return_value = []
        config._original_cluster_id_field.return_value = {}

        log = mock.MagicMock()
        return KafkaConnectCollector(check, config, log), check, config, cache_store

    return _make


@pytest.fixture(scope='session')
def dd_environment():
    """
    Start a kafka cluster and wait for it to be up and running.
    """
    with TempDir() as secret_dir:
        os.chmod(secret_dir, 0o777)
        conditions = []

        if common.AUTHENTICATION == "kerberos":
            common.INSTANCE["sasl_kerberos_keytab"] = common.INSTANCE["sasl_kerberos_keytab"].format(secret_dir)
            conditions.append(WaitFor(wait_for_cp_kafka_topics, attempts=10, wait=10))
            common.E2E_METADATA["docker_volumes"].append(f"{secret_dir}:/var/lib/secret")

        if common.AUTHENTICATION == "ssl":
            conditions.append(WaitFor(wait_for_ssl_ready, attempts=30, wait=5))

        conditions.extend(
            [
                WaitFor(create_topics, attempts=60, wait=3),
                WaitFor(initialize_topics),
                WaitFor(is_cluster_id_available),
            ]
        )

        with docker_run(
            common.DOCKER_IMAGE_PATH,
            conditions=conditions,
            env_vars={
                "KRB5_CONFIG": (
                    f"{common.HERE}/docker/kerberos/kdc/krb5_agent.conf"
                    if running_on_ci()
                    else f"{common.HERE}/docker/kerberos/kdc/krb5_local.conf"
                ),
                "SECRET_DIR": secret_dir,
            },
            build=True,
        ):
            yield (
                {
                    'instances': [common.E2E_INSTANCE],
                    'init_config': {'kafka_timeout': 30},
                },
                common.E2E_METADATA,
            )


def is_cluster_id_available():
    return get_cluster_id() is not None


@pytest.fixture
def check():
    return lambda instance, init_config=None: KafkaCheck('kafka_consumer', init_config or {}, [instance])


@pytest.fixture
def kafka_instance():
    return copy.deepcopy(common.E2E_INSTANCE if e2e_testing() else common.INSTANCE)


def create_topics():
    client = _create_admin_client()
    response = client.list_topics(timeout=1)

    if set(common.TOPICS).issubset(set(response.topics.keys())):
        return True

    for topic in common.TOPICS:
        client.create_topics([NewTopic(topic, 2, 1)])
        time.sleep(1)

    # Make sure the topics in `TOPICS` are created. Brokers may have more topics (such as internal topics)
    # so we only check if it contains the topic we need.
    return set(common.TOPICS).issubset(set(client.list_topics(timeout=1).topics.keys()))


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
    with Producer(common.INSTANCE):
        with Consumer(common.INSTANCE, common.CONSUMED_TOPICS):
            time.sleep(5)


def wait_for_ssl_ready():
    try:
        client = _create_admin_client()
        metadata = client.list_topics(timeout=5)
        return metadata.cluster_id is not None
    except Exception as e:
        print(f"SSL not ready yet: {e}")
        return False


def _create_admin_client():
    config = {
        "bootstrap.servers": common.INSTANCE['kafka_connect_str'],
        "socket.timeout.ms": 5000,  # Increased for SSL handshake
        "topic.metadata.refresh.interval.ms": 2000,
    }
    auth_config = common.get_authentication_configuration(common.INSTANCE)
    config.update(auth_config)

    return AdminClient(config)
