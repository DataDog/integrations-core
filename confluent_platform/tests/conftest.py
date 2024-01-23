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

CONFLUENT_VERSION = os.getenv('CONFLUENT_VERSION')


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

    data_sink = {
        "name": "local-file-sink",
        "config": {
            "name": "local-file-sink",
            "connector.class": "FileStreamSink",
            "tasks.max": "1",
            "file": "/tmp/test.sink.txt",
            "topics": "pageviews",
        },
    }

    requests.post('http://localhost:8083/connectors', data=json.dumps(data_sink), headers=headers)
    requests.post('http://localhost:8083/connectors', data=json.dumps(data), headers=headers)


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file,
        conditions=[
            # Kafka Broker
            CheckDockerLogs('broker', 'Created log for partition _confluent', wait=2),
            # Kafka Schema Registry
            CheckDockerLogs('schema-registry', 'Server started, listening for requests...', attempts=45, wait=2),
            # Kafka Connect
            CheckDockerLogs(
                'connect',
                [' Started KafkaBasedLog', 'INFO REST resources initialized', 'Kafka Connect started'],
                matches='all',
                attempts=120,
                wait=3,
            ),
            # Create connectors
            WaitFor(create_connectors),
            CheckDockerLogs('connect', 'flushing 0 outstanding messages for offset commit'),
        ],
        attempts=3,
    ):
        yield CHECK_CONFIG, {'use_jmx': True}
