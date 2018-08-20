# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.fluentd import Fluentd

from .common import HERE, CHECK_NAME


@pytest.fixture(scope="session")
def spin_up_fluentd(request):
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """

    env = {}

    if not os.environ.get('FLUENTD_VERSION'):
        env['FLUENTD_VERSION'] = 'v0.12.23'

    env['TD_AGENT_CONF_PATH'] = os.path.join(HERE, 'compose', 'td-agent.conf')

    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    with docker_run(compose_file,
                    log_patterns="type monitor_agent",
                    env_vars=env):
        yield


@pytest.fixture
def check():
    return Fluentd(CHECK_NAME, {}, {})
