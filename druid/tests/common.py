# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.dev import get_docker_hostname

HOST = get_docker_hostname()

COORDINATOR_URL = 'http://{}:8081'.format(HOST)
BROKER_URL = 'http://{}:8082'.format(HOST)
