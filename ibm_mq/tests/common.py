# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_DIR = os.path.join(HERE, 'compose')

HOST = get_docker_hostname()
PORT = '11414'

USERNAME = 'admin'
PASSWORD = 'passw0rd'

QUEUE_MANAGER = 'datadog'
CHANNEL = 'DEV.ADMIN.SVRCONN'

QUEUE = 'DEV.QUEUE.1'

BAD_CHANNEL = 'DEV.NOTHERE.SVRCONN'

MQ_VERSION = os.environ.get('IBM_MQ_VERSION', '9')

COMPOSE_FILE_NAME = 'docker-compose-v{}.yml'.format(MQ_VERSION)

COMPOSE_FILE_PATH = os.path.join(COMPOSE_DIR, COMPOSE_FILE_NAME)

INSTANCE = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'queues': [QUEUE],
    'channels': [CHANNEL, BAD_CHANNEL],
}

INSTANCE_QUEUE_PATTERN = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'queue_patterns': ['DEV.*', 'SYSTEM.*'],
    'channels': [CHANNEL, BAD_CHANNEL],
}

INSTANCE_QUEUE_REGEX = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'queue_regex': [r'^DEV\..*$', r'^SYSTEM\..*$'],
    'channels': [CHANNEL, BAD_CHANNEL],
}

INSTANCE_COLLECT_ALL = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'auto_discover_queues': True,
    'channels': [CHANNEL, BAD_CHANNEL],
}

INSTANCE_QUEUE_REGEX_TAG = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'queues': [QUEUE],
    'queue_tag_re': {'DEV.QUEUE.*': "foo:bar"},
}

E2E_METADATA = {
    'start_commands': [
        'mkdir /opt/mqm',
        'curl -o /opt/mqm/mq-client.tar.gz '
        'https://dd-agent-tarball-mirror.s3.amazonaws.com/9.0.0.6-IBM-MQC-Redist-LinuxX64.tar.gz',
        'tar -C /opt/mqm -xf /opt/mqm/mq-client.tar.gz',
    ],
    'env_vars': {'LD_LIBRARY_PATH': '/opt/mqm/lib64:/opt/mqm/lib'},
}
