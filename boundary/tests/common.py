# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
BOUNDARY_VERSION = os.environ['BOUNDARY_VERSION']
SERVER = get_docker_hostname()
PORT = 9203
HEALTH_ENDPOINT = f'http://{SERVER}:{PORT}/health'
METRIC_ENDPOINT = f'http://{SERVER}:{PORT}/metrics'
