import pytest
import os
import subprocess
import requests
import time
import logging
import mock
import getpass

from datadog_checks.utils.platform import Platform

import common

log = logging.getLogger('test_haproxy')


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope="module")
def haproxy_mock():
    filepath = os.path.join(common.HERE, 'fixtures', 'mock_data')
    with open(filepath, 'r') as f:
        data = f.read()
    p = mock.patch('requests.get', return_value=mock.Mock(content=data))
    yield p.start()
    p.stop()


@pytest.fixture(scope="module")
def haproxy_mock_evil():
    filepath = os.path.join(common.HERE, 'fixtures', 'mock_data_evil')
    with open(filepath, 'r') as f:
        data = f.read()
    p = mock.patch('requests.get', return_value=mock.Mock(content=data))
    yield p.start()
    p.stop()


def wait_for_haproxy():
    for _ in xrange(0, 100):
        res = None
        res_open = None
        try:
            auth = (common.USERNAME, common.PASSWORD)
            res = requests.get(common.STATS_URL, auth=auth)
            res.raise_for_status()
            res_open = requests.get(common.STATS_URL_OPEN)
            res_open.raise_for_status()
            return
        except Exception as e:
            log.info("exception: {0} res: {1} res_open: {2}".format(e, res, res_open))
            time.sleep(2)
    raise Exception("Cannot start up apache")


@pytest.fixture(scope="session")
def spin_up_haproxy():
    env = os.environ
    env['HAPROXY_CONFIG_DIR'] = os.path.join(common.HERE, 'compose')
    env['HAPROXY_CONFIG'] = os.path.join(common.HERE, 'compose', 'haproxy.cfg')
    env['HAPROXY_CONFIG_OPEN'] = os.path.join(common.HERE, 'compose', 'haproxy-open.cfg')
    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'haproxy.yaml')
    ]
    subprocess.check_call(args + ["down"], env=env)
    subprocess.check_call(args + ["up", "-d"], env=env)
    wait_for_haproxy()
    if Platform.is_linux():
        # on linux this needs access to the socket
        # it won't work without access
        args = []
        user = getpass.getuser()
        if user != 'root':
            args += ['sudo']
        args += [
            "chown", user, common.UNIXSOCKET_PATH
        ]
        subprocess.check_call(args, env=env)
    time.sleep(20)
    yield
    # subprocess.check_call(args + ["down"], env=env)
