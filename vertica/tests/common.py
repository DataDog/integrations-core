# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

HOST = get_docker_hostname()
PORT = 5433
ID = 'datadog'

CONFIG = {
    'db': ID,
    'server': HOST,
    'port': PORT,
    'username': 'dbadmin',
    'password': 'monitor',
    'timeout': 10,
    'tags': ['foo:bar'],
}

# TODO: Remove
E2E_METADATA = {'start_commands': ['pip install vertica-python==0.9.2']}
