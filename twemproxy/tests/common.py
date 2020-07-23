# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')
ROOT = os.path.dirname(os.path.dirname(HERE))
TESTS_HELPER_DIR = os.path.join(ROOT, 'datadog_checks_tests_helper')
HOST = get_docker_hostname()
PORT = 6222

TWEMPROXY_VERSION = os.environ['TWEMPROXY_VERSION']

INSTANCE = {'host': HOST, 'port': 6222, 'tags': ['optional:tag1']}
