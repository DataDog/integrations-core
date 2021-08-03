# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
MOCKED_INSTANCE = {
    'url': 'mocked',
    'username': 'datadog',
    'password': 'password',
    'tags': ['foo:bar'],
}
