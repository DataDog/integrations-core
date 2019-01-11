# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import time

from six.moves.urllib.request import urlopen
from six.moves.urllib import error
from copy import deepcopy

from datadog_checks.dev import docker_run, WaitFor
from datadog_checks.lighttpd import Lighttpd

from . import common


def wait_for_lighttpd():
    attempts = 0
    while True:
        if attempts > 10:
            return False

        try:
            urlopen(common.STATUS_URL).read()
        except error.HTTPError:
            # endpoint is secured, we do expect 401
            break
        except error.URLError:
            attempts += 1
            time.sleep(1)
    return True


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(common.COMPOSE_FILE, conditions=[WaitFor(wait_for_lighttpd)]):
        instance = deepcopy(common.INSTANCE)
        yield instance


@pytest.fixture
def check():
    check = Lighttpd('lighttpd', {}, {})
    return check


@pytest.fixture
def instance():
    instance = deepcopy(common.INSTANCE)
    return instance
