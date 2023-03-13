# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import socket

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname
from datadog_checks.dev.utils import get_metadata_metrics

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
HOST_IP = socket.gethostbyname(HOST)
KAFKA_CONNECT_STR = f'{HOST_IP}:9092'
TOPICS = ['marvel', 'dc']
PARTITIONS = [0, 1]
BROKER_METRICS = ['kafka.broker_offset']
CONSUMER_METRICS = ['kafka.consumer_offset', 'kafka.consumer_lag']
LEGACY_CLIENT = is_affirmative(os.environ.get('LEGACY_CLIENT', 'false'))
AUTHENTICATION = os.environ.get('AUTHENTICATION', 'noauth')
DOCKER_IMAGE_PATH = os.path.join(HERE, 'docker', AUTHENTICATION, "docker-compose.yaml")

metrics = BROKER_METRICS + CONSUMER_METRICS


def assert_check_kafka(aggregator, consumer_groups):
    for name, consumer_group in consumer_groups.items():
        for topic, partitions in consumer_group.items():
            for partition in partitions:
                tags = [f"topic:{topic}", f"partition:{partition}"] + ['optional:tag1']
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, count=1)

                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(
                        mname,
                        tags=tags + [f"consumer_group:{name}"],
                        count=1,
                    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
