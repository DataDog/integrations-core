# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

PORT = '6379'
PASSWORD = 'devops-best-friend'
MASTER_PORT = '6382'
REPLICA_PORT = '6380'
UNHEALTHY_REPLICA_PORT = '6381'
HOST = get_docker_hostname()
REDIS_VERSION = os.getenv('REDIS_VERSION', 'latest')
CLOUD_ENV = is_affirmative(os.environ['CLOUD_ENV'])

if CLOUD_ENV:
    DOCKER_COMPOSE_PATH = os.path.join(HERE, 'compose', '1m-2s-cloud.compose')
else:
    DOCKER_COMPOSE_PATH = os.path.join(HERE, 'compose', '1m-2s.compose')
