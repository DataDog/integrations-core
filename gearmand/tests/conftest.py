# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.gearmand import Gearman

from .common import HERE, CHECK_NAME


@pytest.fixture(scope="session")
def spin_up_gearmand(request):
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """

    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    with docker_run(compose_file):
        yield


@pytest.fixture
def check():
    return Gearman(CHECK_NAME, {}, {})
