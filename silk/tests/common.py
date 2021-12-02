# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
INSTANCE_LEGACY = {
    'host': '{}'.format(HOST),
    'tags': ['test:silk'],
}
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
