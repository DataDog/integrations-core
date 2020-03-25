# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.base.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

CHECK_NAME = 'rabbitmq'

HOST = get_docker_hostname()
PORT = 15672

URL = 'http://{}:{}/api/'.format(HOST, PORT)

CONFIG = {
    'rabbitmq_api_url': URL,
    'rabbitmq_user': 'guest',
    'rabbitmq_pass': 'guest',
    'queues': ['test1'],
    'tags': ["tag1:1", "tag2"],
    'exchanges': ['test1'],
}

CONFIG_NO_NODES = {
    'rabbitmq_api_url': URL,
    'rabbitmq_user': 'guest',
    'rabbitmq_pass': 'guest',
    'queues': ['test1'],
    'tags': ["tag1:1", "tag2"],
    'exchanges': ['test1'],
    'collect_node_metrics': False,
}

CONFIG_REGEX = {
    'rabbitmq_api_url': URL,
    'rabbitmq_user': 'guest',
    'rabbitmq_pass': 'guest',
    'queues_regexes': [r'test\d+'],
    'exchanges_regexes': [r'test\d+'],
}

CONFIG_VHOSTS = {
    'rabbitmq_api_url': URL,
    'rabbitmq_user': 'guest',
    'rabbitmq_pass': 'guest',
    'vhosts': ['/', 'myvhost'],
}

CONFIG_WITH_FAMILY = {
    'rabbitmq_api_url': URL,
    'rabbitmq_user': 'guest',
    'rabbitmq_pass': 'guest',
    'tag_families': True,
    'queues_regexes': [r'(test)\d+'],
    'exchanges_regexes': [r'(test)\d+'],
}

CONFIG_DEFAULT_VHOSTS = {
    'rabbitmq_api_url': URL,
    'rabbitmq_user': 'guest',
    'rabbitmq_pass': 'guest',
    'vhosts': ['/', 'test'],
}

CONFIG_TEST_VHOSTS = {
    'rabbitmq_api_url': URL,
    'rabbitmq_user': 'guest',
    'rabbitmq_pass': 'guest',
    'vhosts': ['test', 'test2'],
}

EXCHANGE_MESSAGE_STATS = {
    'ack': 1.0,
    'ack_details': {'rate': 1.0},
    'confirm': 1.0,
    'confirm_details': {'rate': 1.0},
    'deliver_get': 1.0,
    'deliver_get_details': {'rate': 1.0},
    'publish': 1.0,
    'publish_details': {'rate': 1.0},
    'publish_in': 1.0,
    'publish_in_details': {'rate': 1.0},
    'publish_out': 1.0,
    'publish_out_details': {'rate': 1.0},
    'return_unroutable': 1.0,
    'return_unroutable_details': {'rate': 1.0},
    'redeliver': 1.0,
    'redeliver_details': {'rate': 1.0},
}
