# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE

E2E_METADATA = {
    'use_jmx': True,
    'start_commands': [
        'mkdir /opt/jboss',
        'curl -o /opt/jboss/jboss-client.jar '
        'https://ddintegrations.blob.core.windows.net/jboss-wildfly/jboss-client.jar',
    ],
}


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(os.path.join(HERE, 'docker', 'docker-compose.yml')):
        instance = load_jmx_config()
        instance['init_config']['custom_jar_paths'] = ['/opt/jboss/jboss-client.jar']
        instance['instances'][0]['jmx_url'] = 'service:jmx:remote+http://{}:9990'.format(get_docker_hostname())
        instance['instances'][0]['user'] = 'datadog'
        instance['instances'][0]['password'] = 'dog'
        yield instance, E2E_METADATA
