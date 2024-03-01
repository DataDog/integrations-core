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
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.kafka_consumer import KafkaCheck

from . import common
from .common import get_cluster_id
from .runners import Consumer, Producer


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
            yield {
                'instances': [common.E2E_INSTANCE],
                'init_config': {'kafka_timeout': 30},
            }, common.E2E_METADATA


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


def _create_admin_client():
    config = {
        "bootstrap.servers": common.INSTANCE['kafka_connect_str'],
        "socket.timeout.ms": 1000,
        "topic.metadata.refresh.interval.ms": 2000,
    }
    config.update(common.get_authentication_configuration(common.INSTANCE))

    return AdminClient(config)
