# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os
import pytest
import socket
import time

from . import common
from datadog_checks.dev import docker_run


log = logging.getLogger('test_twemproxy')


@pytest.fixture(scope="session")
def dd_environment(request):
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """

    env = {}

    env['DOCKER_COMPOSE_FILE'] = common.COMPOSE_FILE
    env['DOCKER_ADDR'] = common.HOST
    env['WAIT_FOR_IT_SCRIPT_PATH'] = _wait_for_it_script()
    env['SETUP_SCRIPT_PATH'] = os.path.join(common.HERE, 'compose', 'setup.sh')

    with docker_run(common.COMPOSE_FILE, env_vars=env):
        if not wait_for_cluster():
            raise Exception("The cluster never came up")
        time.sleep(15)
        yield


def wait_for_cluster():
    for _ in range(0, 10):
        res = None
        try:
            socket.getaddrinfo(common.HOST, common.PORT, 0, 0, socket.IPPROTO_TCP)
            return True
        except Exception as e:
            log.debug("exception: {0} res: {1}".format(e, res))
            time.sleep(5)

    return False


def _wait_for_it_script():
    """
    FIXME: relying on the filesystem layout is a bad idea, the testing helper
    should expose its path through the api instead
    """
    dir = os.path.join(common.TESTS_HELPER_DIR, 'scripts', 'wait-for-it.sh')
    return os.path.abspath(dir)
