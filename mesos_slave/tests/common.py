# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
FIXTURE_DIR = os.path.join(HERE, 'fixtures')
CHECK_NAME = 'mesos_slave'
URL = 'http://{}:5051'.format(get_docker_hostname())

INSTANCE = {'url': URL, 'tasks': ['hello'], 'tags': ['instance:mytag1']}

BAD_INSTANCE = {'url': 'http://localhost:9999', 'tasks': ['hello']}
