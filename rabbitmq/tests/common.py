# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname

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

CONFIG_REGEX = {
    'rabbitmq_api_url': URL,
    'rabbitmq_user': 'guest',
    'rabbitmq_pass': 'guest',
    'queues_regexes': ['test\d+'],
    'exchanges_regexes': ['test\d+']

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
    'queues_regexes': ['(test)\d+'],
    'exchanges_regexes': ['(test)\d+']
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
