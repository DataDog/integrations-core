# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.dev import get_docker_hostname

HOST = get_docker_hostname()

URL = 'http://{}:8080'.format(HOST)
