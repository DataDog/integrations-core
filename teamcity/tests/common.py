# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = '8111'

CHECK_NAME = 'teamcity'

CONFIG = {
    'instances': [
        {
            'name': 'One test build',
            'server': '{}:{}'.format(HOST, PORT),
            'build_configuration': 'TestProject_TestBuild',
            'host_affected': 'buildhost42.dtdg.co',
            'basic_http_authentication': False,
            'is_deployment': False,
            'tags': ['one:tag', 'one:test'],
        },
        {
            'openmetrics_endpoint': 'http://localhost:8111/app/metrics',
        }
    ]
}
