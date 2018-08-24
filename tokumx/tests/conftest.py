# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import os
import pytest
import requests
import subprocess

from datadog_checks.dev import docker_run
from datadog_checks.tokumx import TokuMX

from . import common

@pytest.fixture(scope="session")
def spin_up_tokumx(request):
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """

    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')

    with docker_run(compose_file,
                    log_patterns='admin web console waiting for connections'):
        # cmd = [
        #     'docker-compose',
        #     '-f',
        #     compose_file,
        #     'exec',
        #     'tokumx',
        #     'mongo',
        #     '{}:{}'.format(common.HOST, common.PORT),
        #     '--eval',
        #     '"printjson(db.serverStatus());"'
        # ]
        # subprocess.check_call(cmd)
        yield


@pytest.fixture
def check():
    return TokuMX('tokumx', {}, {})
