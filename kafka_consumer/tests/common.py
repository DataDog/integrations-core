# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import socket
from distutils.version import LooseVersion

from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.utils.common import get_docker_hostname

HOST = get_docker_hostname()
HOST_IP = socket.gethostbyname(HOST)
LAST_ZKONLY_VERSION = (0, 8, 1, 1)
KAFKA_LEGACY = LooseVersion('0.8.2.0')
KAFKA_CONNECT_STR = '{}:9092'.format(HOST_IP)
ZK_CONNECT_STR = '{}:2181'.format(HOST)
TOPICS = ['marvel', 'dc', '__consumer_offsets']
PARTITIONS = [0, 1]


def is_supported(flavors):
    """
    Returns whether the current CI configuration is supported
    """
    supported = False
    version = os.environ.get('KAFKA_VERSION')
    flavor = os.environ.get('KAFKA_OFFSETS_STORAGE', '').lower()

    if not version:
        return False

    for f in flavors:
        if f == flavor:
            supported = True

    if not supported:
        return False

    if version is not 'latest':
        version = version.split('-')[0]
        version = tuple(s for s in version.split('.') if s.strip())
        if flavor is 'kafka' and version <= KafkaCheck.LAST_ZKONLY_VERSION:
            supported = False

    return supported
