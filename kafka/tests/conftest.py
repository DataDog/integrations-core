# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import time

import pytest
from kafka import KafkaConsumer

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE, HOST_IP, KAFKA_CONNECT_STR, TOPICS
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
def dd_environment():
    """
    Start a kafka cluster and wait for it to be up and running.
    """
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yml'),
        conditions=[WaitFor(find_topics, attempts=30, wait=3), initialize_topics],
        env_vars={
            # Advertising the hostname doesn't work on docker:dind so we manually
            # resolve the IP address. This seems to also work outside docker:dind
            'KAFKA_HOST': HOST_IP
        },
    ):
        config = load_jmx_config()
        config['init_config']['collect_default_metrics'] = False
        yield config, {'use_jmx': True}
