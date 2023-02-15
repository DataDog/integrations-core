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
