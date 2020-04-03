# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor

from .common import CHECK_CONFIG, HERE


def create_connectors():
    # Create a dummy connector
    headers = {'Content-type': 'application/json'}
    data = {
        "name": "datagen-pageviews",
        "config": {
            "connector.class": "io.confluent.kafka.connect.datagen.DatagenConnector",
            "key.converter": "org.apache.kafka.connect.storage.StringConverter",
            "kafka.topic": "pageviews",
            "quickstart": "pageviews",
            "max.interval": 100,
            "iterations": 10000000,
            "tasks.max": "1",
        },
    }
    requests.post('http://localhost:8083/connectors', data=json.dumps(data), headers=headers)


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file,
        conditions=[
            # Kafka Broker
            CheckDockerLogs('broker', 'Monitored service is now ready'),
            # Kafka Schema Registry
            CheckDockerLogs('schema-registry', 'Server started, listening for requests...', attempts=90),
            # Kafka Connect
            CheckDockerLogs('connect', 'Kafka Connect started', attempts=120),
            # Create connectors
            WaitFor(create_connectors),
        ],
    ):
        yield CHECK_CONFIG, {'use_jmx': True}
