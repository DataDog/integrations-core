# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import time
from distutils.version import LooseVersion

import docker
from datadog_checks.kafka_consumer import KafkaCheck


LAST_ZKONLY_VERSION = (0, 8, 1, 1)
KAFKA_IMAGE_NAME = 'wurstmeister/kafka'
KAFKA_LEGACY = LooseVersion('0.8.2.0')
CLUSTER_READY = 'Stabilized group my_consumer'
DOCKER_TO = 10
MAX_SETUP_WAIT = 60

KAFKA_CONNECT_STR = '172.19.0.1:9092'
ZK_CONNECT_STR = 'localhost:2181'

TOPICS = ['marvel', 'dc', '__consumer_offsets']
PARTITIONS = [0, 1]

ZK_INSTANCE = {
    'kafka_connect_str': KAFKA_CONNECT_STR,
    'zk_connect_str': ZK_CONNECT_STR,
    # 'zk_prefix': '/0.8',
    'consumer_groups': {
        'my_consumer': {
            'marvel': [0]
        }
    }
}

KAFKA_INSTANCE = {
    'kafka_connect_str': KAFKA_CONNECT_STR,
    'kafka_consumer_offsets': True,
    'tags': ['optional:tag1'],
    'consumer_groups': {
        'my_consumer': {
            'marvel': [0]
        }
    }
}


def is_supported(flavors):
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


def cluster_ready(expected=None):
    start = time.time()

    try:
        cli = docker.from_env()

        nodes = []
        for c in cli.containers:
            if KAFKA_IMAGE_NAME in c.get('Image'):
                nodes.append(c)

        if expected and expected != len(nodes):
            return False

        elapsed = time.time() - start
        while elapsed < MAX_SETUP_WAIT:
            for node in nodes:
                _log = cli.logs(node.get('Id'))
                if CLUSTER_READY in _log:
                    return True

            time.sleep(1)
            elapsed = time.time() - start
    except Exception:
        pass

    return False
