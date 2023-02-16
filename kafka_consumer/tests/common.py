# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import socket

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
HOST_IP = socket.gethostbyname(HOST)
KAFKA_CONNECT_STR = f'{HOST_IP}:9092'
TOPICS = ['marvel', 'dc']
PARTITIONS = [0, 1]
DOCKER_IMAGE_PATH = os.path.join(HERE, 'docker', 'docker-compose.yaml')
KAFKA_VERSION = os.environ.get('KAFKA_VERSION')
BROKER_METRICS = ['kafka.broker_offset']
CONSUMER_METRICS = ['kafka.consumer_offset', 'kafka.consumer_lag']

metrics = BROKER_METRICS + CONSUMER_METRICS


def assert_check_kafka(aggregator, consumer_groups):
    for name, consumer_group in consumer_groups.items():
        for topic, partitions in consumer_group.items():
            for partition in partitions:
                tags = [f"topic:{topic}", f"partition:{partition}"] + ['optional:tag1']
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, at_least=1)
                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(
                        mname,
                        tags=tags + [f"consumer_group:{name}"],
                        at_least=1,
                    )

    aggregator.assert_all_metrics_covered()
