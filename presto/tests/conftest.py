# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.utils import load_jmx_config


@pytest.fixture(scope='session')
def dd_environment(instance):
    with docker_run(os.path.join(get_here(), 'docker', 'docker-compose.yaml'), log_patterns=['SERVER STARTED']):
        yield instance, {'use_jmx': True}


@pytest.fixture(scope='session', autouse=True)
@pytest.mark.usefixtures('dd_environment')
def instance():
    inst = load_jmx_config()
    # Add presto coordinator to the configuration
    inst.get('instances').append(deepcopy(inst.get('instances')[0]))
    inst['instances'][0]['port'] = 9997

    return inst
