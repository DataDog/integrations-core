# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

MEMBER_PORT = 1098
MC_PORT = 9999
MC_HEALTH_CHECK_ENDPOINT = 'http://{}:8081/health'.format(HOST)
