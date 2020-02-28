# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE, HOST_IP


@pytest.fixture(scope='session')
def dd_environment():
    """
    Start a kafka cluster and wait for it to be up and running.
    """
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yml'),
        env_vars={
            # Advertising the hostname doesn't work on docker:dind so we manually
            # resolve the IP address. This seems to also work outside docker:dind
            'KAFKA_HOST': HOST_IP
        },
    ):
        config = load_jmx_config()
        config['init_config']['collect_default_metrics'] = False
        yield config, {'use_jmx': True}
