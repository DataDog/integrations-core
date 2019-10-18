# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

PORT = '6379'
PASSWORD = 'devops-best-friend'
MASTER_PORT = '6382'
REPLICA_PORT = '6380'
UNHEALTHY_REPLICA_PORT = '6381'
HOST = get_docker_hostname()
REDIS_VERSION = os.getenv('REDIS_VERSION', 'latest')
