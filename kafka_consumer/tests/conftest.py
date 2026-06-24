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
def run_connect_check(check, kafka_instance, dd_run_check, datadog_agent):
    """Run a full KafkaCheck cycle with Kafka Connect monitoring enabled.

    Returns the check instance and the mocked Connect HTTP client so tests can assert on
    emitted metrics/events (through the aggregator) and on the outbound Connect requests.
    Depends on ``datadog_agent`` so the persistent cache is reset between tests.
    """

    def _run(
        connectors_response=None,
        connectors_per_run=None,
        plugins_response=None,
        instance_extra=None,
        get_side_effect=None,
        post_response=None,
        post_side_effect=None,
        runs=1,
    ):
        kafka_instance['kafka_connect_url'] = 'http://localhost:8083'
        kafka_instance['enable_cluster_monitoring'] = True
        if instance_extra:
            kafka_instance.update(instance_extra)

        kafka_consumer_check = check(kafka_instance)
        kafka_consumer_check.client = seed_mock_kafka_client()

        responses = connectors_per_run if connectors_per_run is not None else [connectors_response]
        state = {'run': 0}

        def default_get(url, **kwargs):
            response = mock.MagicMock()
            if 'connector-plugins' in url:
                response.json.return_value = [] if plugins_response is None else plugins_response
            else:
                current = responses[min(state['run'], len(responses) - 1)]
                response.json.return_value = {} if current is None else current
            return response

        http = mock.MagicMock()
        http.get.side_effect = get_side_effect or default_get
        if post_side_effect is not None:
            http.post.side_effect = post_side_effect
        elif post_response is not None:
            post = mock.MagicMock()
            post.json.return_value = post_response
            http.post.return_value = post
        kafka_consumer_check._connector_collector.http = http

        with mock.patch.object(kafka_consumer_check.metadata_collector, 'collect_all_metadata'):
            for i in range(runs):
                state['run'] = i
                dd_run_check(kafka_consumer_check)

        return kafka_consumer_check, http

    return _run


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
