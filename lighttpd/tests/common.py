# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
STATUS_URL = 'http://{}:9449/server-status'.format(HOST)
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

INSTANCE = {
    'lighttpd_status_url': STATUS_URL,
    'tags': ['instance:first'],
    'user': 'username',
    'password': 'password',
    'auth_type': 'digest',
}
