# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

HOST = get_docker_hostname()
PORT = 15440
BAD_PORT = 4731

TAGS = ['first_tag', 'second_tag']
TAGS2 = ['foo:bar']

INSTANCE = {
    'server': HOST,
    'port': PORT,
    'tags': TAGS
}

INSTANCE2 = {
    'server': HOST,
    'port': PORT,
    'tags': TAGS2
}

BAD_INSTANCE = {
    'server': HOST,
    'port': BAD_PORT,
    'tags': TAGS2
}

CHECK_NAME = 'gearmand'
