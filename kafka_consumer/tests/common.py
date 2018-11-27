# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import socket

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
HOST_IP = socket.gethostbyname(HOST)
KAFKA_CONNECT_STR = '{}:9092'.format(HOST_IP)
ZK_CONNECT_STR = '{}:2181'.format(HOST)
TOPICS = ['marvel', 'dc', '__consumer_offsets']
PARTITIONS = [0, 1]


def is_supported(flavor):
    """
    Returns whether the current CI configuration is supported
    """
    if not os.environ.get('KAFKA_VERSION'):
        return False

    if flavor != os.environ.get('KAFKA_OFFSETS_STORAGE'):
        return False

    return True
