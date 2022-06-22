# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.dev.utils import ON_WINDOWS

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
SERVER = get_docker_hostname()
ACE_SERVER_NAME = 'ACESERVER'

# https://www.ibm.com/docs/en/app-connect/containers_cd?topic=obtaining-app-connect-enterprise-server-image-from-cloud-container-registry#acedevimages
DOCKER_IMAGE_PREFIX = 'icr.io/appc-dev/ace-server@sha256:'
DOCKER_IMAGE_VERSIONS = {
    '12.0.3.0-r1': f'{DOCKER_IMAGE_PREFIX}9c0ab33cf01233b52e1273e559c1b1daa2f23282430ecd2c48001fc0469132f3',
}

E2E_METADATA = {
    'docker_volumes': ['{}/agent_scripts/start_commands.sh:/tmp/start_commands.sh'.format(HERE)],
    'start_commands': ['bash /tmp/start_commands.sh'],
    'env_vars': {'LD_LIBRARY_PATH': '/opt/mqm/lib64:/opt/mqm/lib', 'C_INCLUDE_PATH': '/opt/mqm/inc'},
}

skip_windows_ci = pytest.mark.skipif(ON_WINDOWS and running_on_ci(), reason='MQ cannot be setup on Windows VMs in CI')
